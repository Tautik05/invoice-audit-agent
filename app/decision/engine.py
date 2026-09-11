from app.schemas.decision import DecisionResult
from app.schemas.enums import (
    DecisionAction,
    ReconciliationStatus,
)
from app.schemas.reconciliation import ReconciliationResult


def decide_invoice_action(
    reconciliation_result: ReconciliationResult,
    duplicate_invoice: bool = False,
) -> DecisionResult:
    """Determine the next action from invoice audit results."""

    if duplicate_invoice:
        return DecisionResult(
            action=DecisionAction.REJECT,
            reasons=[
                "Invoice has already been settled in the ERP."
            ],
        )

    if reconciliation_result.status == (
        ReconciliationStatus.MATCHED
    ):
        return DecisionResult(
            action=DecisionAction.AUTO_APPROVE,
            reasons=[
                "Invoice matches the ERP purchase order."
            ],
        )

    if reconciliation_result.status in {
        ReconciliationStatus.VARIANCE,
        ReconciliationStatus.NOT_FOUND,
        ReconciliationStatus.AMBIGUOUS,
    }:
        return DecisionResult(
            action=DecisionAction.HUMAN_REVIEW,
            reasons=reconciliation_result.errors,
        )

    return DecisionResult(
        action=DecisionAction.HUMAN_REVIEW,
        reasons=[
            "Reconciliation could not be completed safely."
        ],
    )