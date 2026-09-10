from decimal import Decimal
from pathlib import Path

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command

from app.agent.graph import build_audit_graph
from app.agent.state import InvoiceAuditState
from app.agent.tools.erp_tools import ERPTools
from app.config import settings
from app.schemas.extraction import ExtractedInvoice
from app.db.session import SessionLocal

def test_hitl_workflow_persists_and_resumes_from_postgres(
    erp_service,
    session_factory,
    tmp_path,
):
    """Verify that HITL state survives through PostgreSQL."""

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured.")

    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-PG-HITL-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.25"),
        tax=Decimal("500.00"),
        total=Decimal("2500.00"),
    )

    class FakePipeline:
        def process(
            self,
            pdf_path: Path,
            feedback: str | None = None,
        ) -> ExtractedInvoice:
            return extracted_invoice

    document_path = tmp_path / "invoice.pdf"
    document_path.write_bytes(b"fake pdf")

    thread_id = "postgres-hitl-test-001"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    database_url = settings.database_url

    with PostgresSaver.from_conn_string(
        database_url
    ) as checkpointer:

        checkpointer.setup()

        graph = build_audit_graph(
            ERPTools(erp_service),
            extraction_pipeline=FakePipeline(),
            checkpointer=checkpointer,
            session_factory=session_factory,
        )

        interrupted_result = graph.invoke(
            {
                "workflow_id": thread_id,
                "document_path": str(document_path),
                "extraction_attempts": 0,
                "reflection_feedback": None,
            },
            config=config,
        )

        assert "__interrupt__" in interrupted_result

    # The original graph/checkpointer context has now closed.
    #
    # Create a completely new checkpointer and graph and
    # resume using only the same thread_id.

    with PostgresSaver.from_conn_string(
        database_url
    ) as checkpointer:

        graph = build_audit_graph(
            ERPTools(erp_service),
            extraction_pipeline=FakePipeline(),
            checkpointer=checkpointer,
            session_factory=session_factory,
        )

        resumed_result = graph.invoke(
            Command(resume="approved"),
            config=config,
        )

        assert (
            resumed_result["human_decision"].value
            == "approved"
        )

        assert (
            resumed_result["workflow_status"].value
            == "completed"
        )