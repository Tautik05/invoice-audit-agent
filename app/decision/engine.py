from app.schemas.decision import DecisionResult
from app.schemas.enums import (
    DecisionAction,
    ReconciliationStatus,
)
from app.schemas.reconciliation import ReconciliationResult


def decide_invoice_action(
    reconciliation_result: ReconciliationResult,
) -> DecisionResult:
    """Determine the next action from reconciliation results."""

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