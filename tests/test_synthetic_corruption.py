from decimal import Decimal
from random import Random
from faker import Faker
from app.schemas.synthetic import SyntheticInvoiceRecord
from app.synthetic.corruption import (
    CorruptionType,
    corrupt_currency,
    corrupt_subtotal,
    corrupt_tax,
    corrupt_total,
    remove_po,
)
from scripts.generate_invoices import generate_invoice


def make_invoice() -> SyntheticInvoiceRecord:
    faker = Faker()
    faker.seed_instance(42)

    rng = Random(42)

    return generate_invoice(
        faker=faker,
        rng=rng,
        invoice_number=1,
    )


def test_corrupt_tax_does_not_modify_ground_truth():
    invoice = make_invoice()

    original_tax = invoice.tax
    original_total = invoice.total

    result = corrupt_tax(invoice)

    assert result.corruption_type == CorruptionType.TAX_MISMATCH

    assert invoice.tax == original_tax
    assert invoice.total == original_total

    assert result.invoice.tax == original_tax + Decimal("10.00")
    assert result.invoice.total == (
        result.invoice.subtotal + result.invoice.tax
    )


def test_corrupt_subtotal():
    invoice = make_invoice()

    result = corrupt_subtotal(invoice)

    assert result.corruption_type == CorruptionType.SUBTOTAL_MISMATCH

    assert result.invoice.subtotal == (
        invoice.subtotal + Decimal("10.00")
    )

    assert result.invoice.total == (
        result.invoice.subtotal + result.invoice.tax
    )

    assert invoice.subtotal != result.invoice.subtotal


def test_corrupt_total():
    invoice = make_invoice()

    result = corrupt_total(invoice)

    assert result.corruption_type == CorruptionType.TOTAL_MISMATCH

    assert result.invoice.total == (
        invoice.total + Decimal("10.00")
    )

    assert result.invoice.subtotal == invoice.subtotal
    assert result.invoice.tax == invoice.tax


def test_remove_po():
    invoice = make_invoice()

    assert invoice.po_number is not None

    result = remove_po(invoice)

    assert result.corruption_type == CorruptionType.MISSING_PO
    assert result.invoice.po_number is None

    # Ground truth remains unchanged.
    assert invoice.po_number is not None


def test_corrupt_currency():
    invoice = make_invoice()

    original_currency = invoice.currency

    result = corrupt_currency(invoice)

    assert result.corruption_type == CorruptionType.CURRENCY_MISMATCH

    assert result.invoice.currency != original_currency
    assert result.invoice.currency in {"USD", "EUR", "GBP", "INR"}

    # Ground truth remains unchanged.
    assert invoice.currency == original_currency