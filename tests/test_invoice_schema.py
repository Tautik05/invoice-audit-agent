from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.invoice import Invoice


def test_valid_invoice():
    invoice = Invoice(
        invoice_number="INV-10492",
        vendor="ABC Supplies",
        invoice_date=date(2026, 8, 31),
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )

    assert invoice.vendor == "ABC Supplies"
    assert invoice.total == Decimal("2360.00")


def test_invalid_quantity():
    with pytest.raises(ValidationError):
        Invoice(
            invoice_number="INV-10492",
            vendor="ABC Supplies",
            currency="USD",
            line_items=[
                {
                    "description": "Monitor",
                    "quantity": 0,
                    "unit_price": Decimal("200.00"),
                }
            ],
            subtotal=Decimal("2000.00"),
            tax_rate=Decimal("0.18"),
            tax=Decimal("360.00"),
            total=Decimal("2360.00"),
        )