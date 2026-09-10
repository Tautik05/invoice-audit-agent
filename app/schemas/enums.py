from enum import Enum


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"


class ReconciliationStatus(str, Enum):
    MATCHED = "matched"
    VARIANCE = "variance"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"
    FAILED = "failed"


class HumanDecision(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"


class InvoiceStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    APPROVED = "approved"
    REJECTED = "rejected"
    SETTLED = "settled"

class DecisionAction(str, Enum):
    AUTO_APPROVE = "auto_approve"
    HUMAN_REVIEW = "human_review"
    REJECT = "reject"


class AuditEventType(str, Enum):
    EXTRACTION_COMPLETED = "extraction_completed"
    VALIDATION_COMPLETED = "validation_completed"
    RECONCILIATION_COMPLETED = "reconciliation_completed"
    DECISION_MADE = "decision_made"
    HUMAN_REVIEW_REQUESTED = "human_review_requested"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"
    INVOICE_SETTLED = "invoice_settled"