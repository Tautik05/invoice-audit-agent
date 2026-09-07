from decimal import Decimal

from app.decision.engine import decide_invoice_action
from app.schemas.enums import (
    DecisionAction,
    ReconciliationStatus,
)
from app.schemas.reconciliation import ReconciliationResult


def make_result(
    status: ReconciliationStatus,
    errors: list[str] | None = None,
) -> ReconciliationResult:
    return ReconciliationResult(
        status=status,
        po_found=status != ReconciliationStatus.NOT_FOUND,
        vendor_matched=True,
        currency_matched=True,
        line_items_matched=True,
        invoice_total=Decimal("2360.00"),
        po_total=Decimal("2360.00"),
        variance=Decimal("0.00"),
        errors=errors or [],
    )


def test_matched_invoice_is_auto_approved():
    result = make_result(
        ReconciliationStatus.MATCHED
    )

    decision = decide_invoice_action(result)

    assert (
        decision.action
        == DecisionAction.AUTO_APPROVE
    )
    assert decision.reasons


def test_variance_requires_human_review():
    result = make_result(
        ReconciliationStatus.VARIANCE,
        ["Invoice total does not match PO total."],
    )

    decision = decide_invoice_action(result)

    assert (
        decision.action
        == DecisionAction.HUMAN_REVIEW
    )
    assert (
        "Invoice total does not match PO total."
        in decision.reasons
    )


def test_missing_po_requires_human_review():
    result = make_result(
        ReconciliationStatus.NOT_FOUND,
        ["Purchase order not found."],
    )

    decision = decide_invoice_action(result)

    assert (
        decision.action
        == DecisionAction.HUMAN_REVIEW
    )


def test_ambiguous_po_requires_human_review():
    result = make_result(
        ReconciliationStatus.AMBIGUOUS,
        ["Multiple purchase orders matched."],
    )

    decision = decide_invoice_action(result)

    assert (
        decision.action
        == DecisionAction.HUMAN_REVIEW
    )


def test_failed_reconciliation_defaults_to_human_review():
    result = make_result(
        ReconciliationStatus.FAILED,
        ["ERP lookup failed."],
    )

    decision = decide_invoice_action(result)

    assert (
        decision.action
        == DecisionAction.HUMAN_REVIEW
    )