from decimal import Decimal

import pytest

from app.extraction.response_normalizer import (
    normalize_decimal,
    normalize_extraction_response,
)


def test_normalize_decimal_currency() -> None:
    assert normalize_decimal(
        "$2,000.00"
    ) == Decimal("2000.00")


def test_normalize_decimal_percentage() -> None:
    assert normalize_decimal(
        "18%",
        percentage=True,
    ) == Decimal("0.18")


def test_normalize_extraction_response() -> None:
    response = """
    {
        "invoice_number": " INV-1001 ",
        "vendor": " ABC Supplies ",
        "invoice_date": "2026-09-01",
        "po_number": " PO-8821 ",
        "currency": " usd ",
        "line_items": [
            {
                "description": " Monitor ",
                "quantity": 10,
                "unit_price": "$200.00"
            }
        ],
        "subtotal": "$2,000.00",
        "tax_rate": "18%",
        "tax": "$360.00",
        "total": "$2,360.00"
    }
    """

    invoice = normalize_extraction_response(
        response
    )

    assert invoice.invoice_number == "INV-1001"
    assert invoice.vendor == "ABC Supplies"
    assert invoice.po_number == "PO-8821"
    assert invoice.currency == "USD"

    assert len(invoice.line_items) == 1
    assert (
        invoice.line_items[0].description
        == "Monitor"
    )
    assert (
        invoice.line_items[0].unit_price
        == Decimal("200.00")
    )

    assert invoice.subtotal == Decimal("2000.00")
    assert invoice.tax_rate == Decimal("0.18")
    assert invoice.tax == Decimal("360.00")
    assert invoice.total == Decimal("2360.00")


def test_normalize_extraction_response_rejects_missing_fields() -> None:
    response = """
    {
        "invoice_number": "INV-1001",
        "vendor": "ABC Supplies",
        "currency": "USD",
        "subtotal": "2000.00",
        "tax_rate": "18%",
        "tax": "360.00",
        "total": "2360.00"
    }
    """

    with pytest.raises(
        ValueError,
        match="missing required fields",
    ):
        normalize_extraction_response(
            response
        )