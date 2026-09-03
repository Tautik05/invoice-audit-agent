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