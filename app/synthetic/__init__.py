from copy import deepcopy
from decimal import Decimal
from enum import Enum

from app.schemas.synthetic import SyntheticInvoiceRecord


class CorruptionType(str, Enum):
    TAX_MISMATCH = "tax_mismatch"
    SUBTOTAL_MISMATCH = "subtotal_mismatch"
    TOTAL_MISMATCH = "total_mismatch"
    MISSING_PO = "missing_po"
    CURRENCY_MISMATCH = "currency_mismatch"
    FORMATTING = "formatting"


class CorruptionResult:
    """Contains corrupted invoice data and metadata."""

    def __init__(
        self,
        invoice: SyntheticInvoiceRecord,
        corruption_type: CorruptionType,
        description: str,
    ) -> None:
        self.invoice = invoice
        self.corruption_type = corruption_type
        self.description = description


def corrupt_tax(
    invoice: SyntheticInvoiceRecord,
) -> CorruptionResult:
    """Create an invoice with an incorrect tax amount."""

    corrupted = deepcopy(invoice)

    corrupted.tax = corrupted.tax + Decimal("10.00")
    corrupted.total = corrupted.subtotal + corrupted.tax

    return CorruptionResult(
        invoice=corrupted,
        corruption_type=CorruptionType.TAX_MISMATCH,
        description="Tax amount was increased by 10.00.",
    )


def corrupt_subtotal(
    invoice: SyntheticInvoiceRecord,
) -> CorruptionResult:
    """Create an invoice with an incorrect subtotal."""

    corrupted = deepcopy(invoice)

    corrupted.subtotal = corrupted.subtotal + Decimal("10.00")
    corrupted.total = corrupted.subtotal + corrupted.tax

    return CorruptionResult(
        invoice=corrupted,
        corruption_type=CorruptionType.SUBTOTAL_MISMATCH,
        description="Subtotal was increased by 10.00.",
    )


def corrupt_total(
    invoice: SyntheticInvoiceRecord,
) -> CorruptionResult:
    """Create an invoice with an incorrect total."""

    corrupted = deepcopy(invoice)

    corrupted.total = corrupted.total + Decimal("10.00")

    return CorruptionResult(
        invoice=corrupted,
        corruption_type=CorruptionType.TOTAL_MISMATCH,
        description="Total was increased by 10.00.",
    )


def remove_po(
    invoice: SyntheticInvoiceRecord,
) -> CorruptionResult:
    """Create an invoice without a purchase order number."""

    corrupted = deepcopy(invoice)

    corrupted.po_number = None

    return CorruptionResult(
        invoice=corrupted,
        corruption_type=CorruptionType.MISSING_PO,
        description="Purchase order number was removed.",
    )


def corrupt_currency(
    invoice: SyntheticInvoiceRecord,
) -> CorruptionResult:
    """Change the invoice currency to another supported currency."""

    corrupted = deepcopy(invoice)

    supported_currencies = ["USD", "EUR", "GBP", "INR"]

    alternatives = [
        currency
        for currency in supported_currencies
        if currency != corrupted.currency
    ]

    corrupted.currency = alternatives[0]

    return CorruptionResult(
        invoice=corrupted,
        corruption_type=CorruptionType.CURRENCY_MISMATCH,
        description=(
            f"Currency changed from {invoice.currency} "
            f"to {corrupted.currency}."
        ),
    )