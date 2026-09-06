from decimal import Decimal

import pytest

from app.extraction.response_normalizer import (
    normalize_decimal,
    normalize_extraction_response,
    normalize_optional_identifier,
)


def test_normalize_decimal_currency() -> None:
    assert normalize_decimal(
        "$2,000.00"
    ) == Decimal("2000.00")


def test_normalize_decimal_percentage_with_symbol() -> None:
    assert normalize_decimal(
        "18%",
        percentage=True,
    ) == Decimal("0.18")


def test_normalize_decimal_percentage_without_symbol() -> None:
    assert normalize_decimal(
        "18",
        percentage=True,
    ) == Decimal("0.18")


def test_normalize_decimal_fractional_percentage() -> None:
    assert normalize_decimal(
        "0.18",
        percentage=True,
    ) == Decimal("0.18")


def test_normalize_decimal_twenty_percent() -> None:
    assert normalize_decimal(
        "20",
        percentage=True,
    ) == Decimal("0.20")


def test_normalize_decimal_twenty_percent_with_symbol() -> None:
    assert normalize_decimal(
        "20%",
        percentage=True,
    ) == Decimal("0.20")


def test_normalize_decimal_rejects_invalid_percentage() -> None:
    with pytest.raises(
        ValueError,
        match="Percentage value out of range",
    ):
        normalize_decimal(
            "150",
            percentage=True,
        )


def test_normalize_optional_identifier_with_value() -> None:
    assert normalize_optional_identifier(
        " PO-8821 "
    ) == "PO-8821"


def test_normalize_optional_identifier_with_na() -> None:
    assert normalize_optional_identifier(
        "N/A"
    ) is None


def test_normalize_optional_identifier_with_na_variants() -> None:
    assert normalize_optional_identifier("NA") is None
    assert normalize_optional_identifier("N.A.") is None
    assert normalize_optional_identifier("NONE") is None
    assert normalize_optional_identifier("NULL") is None
    assert normalize_optional_identifier("-") is None


def test_normalize_optional_identifier_with_empty_value() -> None:
    assert normalize_optional_identifier("") is None
    assert normalize_optional_identifier("   ") is None
    assert normalize_optional_identifier(None) is None


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


def test_normalize_extraction_response_normalizes_missing_po() -> None:
    response = """
    {
        "invoice_number": "INV-00003",
        "vendor": "Hoffman Ltd",
        "invoice_date": "2026-05-13",
        "po_number": "N/A",
        "currency": "INR",
        "line_items": [
            {
                "description": "Headset",
                "quantity": 15,
                "unit_price": "1256.00"
            },
            {
                "description": "Docking Station",
                "quantity": 9,
                "unit_price": "1707.00"
            }
        ],
        "subtotal": "34203.00",
        "tax_rate": "18%",
        "tax": "6156.54",
        "total": "40359.54"
    }
    """

    invoice = normalize_extraction_response(
        response
    )

    assert invoice.invoice_number == "INV-00003"
    assert invoice.vendor == "Hoffman Ltd"
    assert invoice.po_number is None
    assert invoice.currency == "INR"
    assert invoice.tax_rate == Decimal("0.18")


def test_normalize_extraction_response_handles_null_po() -> None:
    response = """
    {
        "invoice_number": "INV-00003",
        "vendor": "Hoffman Ltd",
        "currency": "INR",
        "po_number": null,
        "line_items": [
            {
                "description": "Headset",
                "quantity": 15,
                "unit_price": "1256.00"
            }
        ],
        "subtotal": "18840.00",
        "tax_rate": "18%",
        "tax": "3391.20",
        "total": "22231.20"
    }
    """

    invoice = normalize_extraction_response(
        response
    )

    assert invoice.po_number is None


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