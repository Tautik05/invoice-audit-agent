from decimal import Decimal

from app.schemas.enums import ValidationStatus
from app.schemas.invoice import Invoice
from app.schemas.validation import ValidationResult

from app.validation.arithmetic import (
    calculate_subtotal,
    calculate_tax,
    calculate_total,
)
from app.validation.currency import validate_currency


MONEY_TOLERANCE = Decimal("0.01")


def amounts_match(expected: Decimal, actual: Decimal) -> bool:
    """Check whether two monetary values are within tolerance."""
    return abs(expected - actual) <= MONEY_TOLERANCE


def validate_invoice(invoice: Invoice) -> ValidationResult:
    """Run deterministic validation checks on an invoice."""

    calculated_subtotal = calculate_subtotal(invoice)
    calculated_tax = calculate_tax(invoice)
    calculated_total = calculate_total(invoice)

    subtotal_valid = amounts_match(
        calculated_subtotal,
        invoice.subtotal,
    )

    tax_valid = amounts_match(
        calculated_tax,
        invoice.tax,
    )

    total_valid = amounts_match(
        calculated_total,
        invoice.total,
    )

    currency_valid = validate_currency(invoice)

    errors: list[str] = []

    if not subtotal_valid:
        errors.append(
            f"Subtotal mismatch: "
            f"expected {calculated_subtotal}, "
            f"got {invoice.subtotal}"
        )

    if not tax_valid:
        errors.append(
            f"Tax mismatch: "
            f"expected {calculated_tax}, "
            f"got {invoice.tax}"
        )

    if not total_valid:
        errors.append(
            f"Total mismatch: "
            f"expected {calculated_total}, "
            f"got {invoice.total}"
        )

    if not currency_valid:
        errors.append(
            f"Unsupported currency: {invoice.currency}"
        )

    status = (
        ValidationStatus.PASSED
        if not errors
        else ValidationStatus.FAILED
    )

    return ValidationResult(
        status=status,
        calculated_subtotal=calculated_subtotal,
        calculated_tax=calculated_tax,
        calculated_total=calculated_total,
        subtotal_valid=subtotal_valid,
        tax_valid=tax_valid,
        total_valid=total_valid,
        currency_valid=currency_valid,
        errors=errors,
    )