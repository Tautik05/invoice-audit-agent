from pydantic import BaseModel


class InvoiceSubmissionResponse(BaseModel):
    """Response returned after submitting an invoice."""

    workflow_id: str
    status: str
    message: str