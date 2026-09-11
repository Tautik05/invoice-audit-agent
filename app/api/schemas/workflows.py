from pydantic import BaseModel


class WorkflowResponse(BaseModel):
    """Current workflow status."""

    workflow_id: str
    status: str
    message: str


class AuditEventResponse(BaseModel):
    """Audit event exposed through the API."""

    id: int
    workflow_id: str
    event_type: str
    actor: str
    details: dict | None
    created_at: str


class WorkflowAuditResponse(BaseModel):
    """Audit history for a workflow."""

    workflow_id: str
    events: list[AuditEventResponse]