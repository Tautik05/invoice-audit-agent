from random import Random

from faker import Faker

from scripts.generate_invoices import generate_invoice
from app.schemas.synthetic import SyntheticInvoiceRecord


def test_generate_invoice():
    faker = Faker()
    faker.seed_instance(42)

    rng = Random(42)

    invoice = generate_invoice(
        faker=faker,
        rng=rng,
        invoice_number=1,
    )

    assert isinstance(invoice, SyntheticInvoiceRecord)

    assert invoice.invoice_number == "INV-00001"
    assert invoice.vendor
    assert invoice.currency in {"USD", "EUR", "GBP", "INR"}

    assert len(invoice.line_items) >= 1

    assert invoice.subtotal >= 0
    assert invoice.tax >= 0
    assert invoice.total >= 0


def test_generated_invoice_math_is_consistent():
    faker = Faker()
    faker.seed_instance(42)

    rng = Random(42)

    invoice = generate_invoice(
        faker=faker,
        rng=rng,
        invoice_number=1,
    )

    calculated_subtotal = sum(
        (
            item.quantity * item.unit_price
            for item in invoice.line_items
        ),
    )

    calculated_tax = (
        calculated_subtotal * invoice.tax_rate
    )

    calculated_total = (
        calculated_subtotal + calculated_tax
    )

    assert invoice.subtotal == calculated_subtotal.quantize(
        invoice.subtotal
    )

    assert invoice.tax == calculated_tax.quantize(
        invoice.tax
    )

    assert invoice.total == calculated_total.quantize(
        invoice.total
    )