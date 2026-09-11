from typing import TypedDict

from app.schemas.decision import DecisionResult
from app.schemas.enums import HumanDecision, WorkflowStatus
from app.schemas.invoice import Invoice
from app.schemas.reconciliation import ReconciliationResult
from app.schemas.validation import ValidationResult


class InvoiceAuditState(TypedDict, total=False):
    workflow_id: str
    document_path: str
    invoice: Invoice
    validation_result: ValidationResult | None
    duplicate_invoice: bool
    reconciliation_result: ReconciliationResult | None
    decision_result: DecisionResult | None
    workflow_status: WorkflowStatus
    extraction_attempts: int
    reflection_feedback: str | None
    human_approval_required: bool
    human_decision: HumanDecision | None
    error: str | None