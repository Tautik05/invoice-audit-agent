from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.extraction.normalizer import normalize_invoice
from app.schemas.extraction import ExtractedInvoice
from app.schemas.invoice import Invoice


def make_extracted_invoice(
    *,
    vendor: str = "ABC Supplies",
    currency: str = "USD",
    po_number: str | None = "PO-8821",
    quantity: int = 10,
) -> ExtractedInvoice:
    return ExtractedInvoice(
        invoice_number="INV-1001",
        vendor=vendor,
        invoice_date=date(2026, 9, 1),
        po_number=po_number,
        currency=currency,
        line_items=[
            {
                "description": " Monitor ",
                "quantity": quantity,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )


def test_normalize_invoice():
    extracted = make_extracted_invoice(
        vendor=" ABC Supplies ",
        currency=" usd ",
        po_number=" PO-8821 ",
    )

    invoice = normalize_invoice(extracted)

    assert isinstance(invoice, Invoice)

    assert invoice.invoice_number == "INV-1001"
    assert invoice.vendor == "ABC Supplies"
    assert invoice.currency == "USD"
    assert invoice.po_number == "PO-8821"

    assert invoice.line_items[0].description == "Monitor"
    assert invoice.line_items[0].quantity == 10
    assert invoice.line_items[0].unit_price == Decimal("200.00")


def test_normalize_invoice_without_po():
    extracted = make_extracted_invoice(po_number=None)

    invoice = normalize_invoice(extracted)

    assert isinstance(invoice, Invoice)
    assert invoice.po_number is None


def test_normalize_invoice_rejects_invalid_quantity():
    extracted = make_extracted_invoice(quantity=0)

    with pytest.raises(ValidationError):
        normalize_invoice(extracted)