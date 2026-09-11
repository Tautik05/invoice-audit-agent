import json

from fastapi import APIRouter, HTTPException, Request
from langgraph.types import Command

from app.api.schemas.workflows import (
    AuditEventResponse,
    WorkflowAuditResponse,
    WorkflowResponse,
)
from app.erp.repository import ERPRepository
import logging



router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
)

logger = logging.getLogger(__name__)

def _get_workflow_state(
    workflow_id: str,
    request: Request,
):
    """Return the persisted state for a workflow."""
    graph = request.app.state.audit_graph

    state = graph.get_state(
        {
            "configurable": {
                "thread_id": workflow_id,
            }
        }
    )

    if state is None or not state.values:
        raise HTTPException(
            status_code=404,
            detail="Workflow not found.",
        )

    return state


def _status_value(workflow_status) -> str:
    """Return a workflow status as a plain string."""
    return (
        workflow_status.value
        if hasattr(workflow_status, "value")
        else workflow_status
    )


def _require_human_review(
    workflow_id: str,
    request: Request,
):
    """Ensure the workflow is currently awaiting human review."""
    state = _get_workflow_state(
        workflow_id,
        request,
    )

    workflow_status = state.values.get("workflow_status")

    if workflow_status is None:
        raise HTTPException(
            status_code=500,
            detail="Workflow has no status.",
        )

    status = _status_value(workflow_status)

    if status != "waiting_for_human":
        raise HTTPException(
            status_code=409,
            detail=(
                "Workflow is not awaiting human review. "
                f"Current status: {status}."
            ),
        )

    return state


@router.get(
    "/{workflow_id}/audit",
    response_model=WorkflowAuditResponse,
)
def get_workflow_audit(
    workflow_id: str,
    request: Request,
) -> WorkflowAuditResponse:
    """Return the audit history for a workflow."""
    session_factory = request.app.state.session_factory

    with session_factory() as session:
        repository = ERPRepository(session)
        events = repository.get_audit_events(workflow_id)

    return WorkflowAuditResponse(
        workflow_id=workflow_id,
        events=[
            AuditEventResponse(
                id=event.id,
                workflow_id=event.workflow_id,
                event_type=event.event_type,
                actor=event.actor,
                details=(
                    json.loads(event.details)
                    if event.details
                    else None
                ),
                created_at=event.created_at.isoformat(),
            )
            for event in events
        ],
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowResponse,
)
def get_workflow(
    workflow_id: str,
    request: Request,
) -> WorkflowResponse:
    """Return the current status of a workflow."""
    state = _get_workflow_state(
        workflow_id,
        request,
    )

    workflow_status = state.values.get("workflow_status")

    if workflow_status is None:
        raise HTTPException(
            status_code=500,
            detail="Workflow has no status.",
        )

    status = _status_value(workflow_status)

    messages = {
        "waiting_for_human": "Invoice requires human review.",
        "completed": "Invoice processing completed.",
        "rejected": "Invoice was rejected.",
        "failed": "Invoice processing failed.",
        "running": "Invoice is currently being processed.",
        "pending": "Invoice is pending processing.",
    }

    return WorkflowResponse(
        workflow_id=workflow_id,
        status=status,
        message=messages.get(
            status,
            "Workflow status retrieved.",
        ),
    )


@router.post(
    "/{workflow_id}/approve",
    response_model=WorkflowResponse,
)
def approve_workflow(
    workflow_id: str,
    request: Request,
) -> WorkflowResponse:
    """Approve a workflow waiting for human review."""
    _require_human_review(
        workflow_id,
        request,
    )

    graph = request.app.state.audit_graph

    try:
        graph.invoke(
            Command(resume="approved"),
            config={
                "configurable": {
                    "thread_id": workflow_id,
                }
            },
        )
    except Exception as exc:
        logger.exception(
            "Failed to reject workflow %s",
            workflow_id,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to reject workflow.",
        ) from exc

    state = graph.get_state(
        {
            "configurable": {
                "thread_id": workflow_id,
            }
        }
    )

    workflow_status = state.values.get("workflow_status")

    if workflow_status is None:
        raise HTTPException(
            status_code=500,
            detail="Workflow has no status after approval.",
        )

    status = _status_value(workflow_status)

    return WorkflowResponse(
        workflow_id=workflow_id,
        status=status,
        message="Workflow approved successfully.",
    )


@router.post(
    "/{workflow_id}/reject",
    response_model=WorkflowResponse,
)
def reject_workflow(
    workflow_id: str,
    request: Request,
) -> WorkflowResponse:
    """Reject a workflow waiting for human review."""
    _require_human_review(
        workflow_id,
        request,
    )

    graph = request.app.state.audit_graph

    try:
        graph.invoke(
            Command(resume="rejected"),
            config={
                "configurable": {
                    "thread_id": workflow_id,
                }
            },
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to reject workflow.",
        ) from exc

    state = graph.get_state(
        {
            "configurable": {
                "thread_id": workflow_id,
            }
        }
    )

    workflow_status = state.values.get("workflow_status")

    if workflow_status is None:
        raise HTTPException(
            status_code=500,
            detail="Workflow has no status after rejection.",
        )

    status = _status_value(workflow_status)

    return WorkflowResponse(
        workflow_id=workflow_id,
        status=status,
        message="Workflow rejected successfully.",
    )