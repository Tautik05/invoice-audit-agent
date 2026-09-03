from typing import TypedDict

from app.schemas.enums import WorkflowStatus
from app.schemas.invoice import Invoice
from app.schemas.reconciliation import ReconciliationResult
from app.schemas.validation import ValidationResult


class InvoiceAuditState(TypedDict, total=False):
    workflow_id: str

    invoice: Invoice

    validation_result: ValidationResult | None
    reconciliation_result: ReconciliationResult | None

    workflow_status: WorkflowStatus

    extraction_attempts: int
    human_approval_required: bool
    human_approved: bool

    error: str | None