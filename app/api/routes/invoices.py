import logging
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Request, UploadFile

from app.api.schemas.invoices import InvoiceSubmissionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/invoices", tags=["invoices"])


@router.post(
    "",
    response_model=InvoiceSubmissionResponse,
)
def submit_invoice(
    request: Request,
    file: UploadFile = File(...),
) -> InvoiceSubmissionResponse:
    """Submit an invoice PDF for autonomous auditing."""

    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted.",
        )

    workflow_id = str(uuid4())

    temporary_file = NamedTemporaryFile(
        suffix=".pdf",
        delete=False,
    )
    document_path = Path(temporary_file.name)

    try:
        with temporary_file:
            while chunk := file.file.read(1024 * 1024):
                temporary_file.write(chunk)

        graph = request.app.state.audit_graph

        result = graph.invoke(
            {
                "workflow_id": workflow_id,
                "document_path": str(document_path),
                "extraction_attempts": 0,
                "reflection_feedback": None,
            },
            config={
                "configurable": {
                    "thread_id": workflow_id,
                }
            },
        )

        if "__interrupt__" in result:
            return InvoiceSubmissionResponse(
                workflow_id=workflow_id,
                status="waiting_for_human",
                message="Invoice requires human review.",
            )

        workflow_status = result.get("workflow_status")

        if workflow_status is None:
            raise RuntimeError(
                "Workflow completed without a workflow status."
            )

        return InvoiceSubmissionResponse(
            workflow_id=workflow_id,
            status=workflow_status.value,
            message="Invoice processing completed.",
        )

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Invoice processing failed for workflow %s",
            workflow_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Invoice processing failed.",
        ) from exc

    finally:
        document_path.unlink(missing_ok=True)