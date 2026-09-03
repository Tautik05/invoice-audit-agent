from decimal import Decimal

from app.schemas.enums import ValidationStatus
from app.schemas.invoice import Invoice
from app.validation.engine import validate_invoice


def make_invoice(
    *,
    subtotal="2000.00",
    tax="360.00",
    total="2360.00",
    tax_rate="0.18",
    currency="USD",
):
    return Invoice(
        invoice_number="INV-001",
        vendor="ABC Supplies",
        po_number="PO-001",
        currency=currency,
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal(subtotal),
        tax_rate=Decimal(tax_rate),
        tax=Decimal(tax),
        total=Decimal(total),
    )


def test_valid_invoice():
    invoice = make_invoice()

    result = validate_invoice(invoice)

    assert result.status == ValidationStatus.PASSED
    assert result.subtotal_valid is True
    assert result.tax_valid is True
    assert result.total_valid is True
    assert result.currency_valid is True
    assert result.errors == []


def test_invalid_subtotal():
    invoice = make_invoice(
        subtotal="2500.00",
    )

    result = validate_invoice(invoice)

    assert result.status == ValidationStatus.FAILED
    assert result.subtotal_valid is False
    assert result.tax_valid is True
    assert result.total_valid is True
    assert len(result.errors) == 1


def test_invalid_tax():
    invoice = make_invoice(
        tax="400.00",
        total="2400.00",
    )

    result = validate_invoice(invoice)

    assert result.status == ValidationStatus.FAILED
    assert result.tax_valid is False
    assert result.total_valid is False


def test_invalid_currency():
    invoice = make_invoice(
        currency="XYZ",
    )

    result = validate_invoice(invoice)

    assert result.status == ValidationStatus.FAILED
    assert result.currency_valid is False