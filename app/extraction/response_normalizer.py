import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any

from app.schemas.extraction import (
    ExtractedInvoice,
    ExtractedInvoiceLineItem,
)


def normalize_decimal(
    value: Any,
    *,
    percentage: bool = False,
) -> Decimal:
    """
    Convert common LLM numeric representations into Decimal.

    For percentage fields, both percentage-point and fractional
    representations are normalized to a fractional Decimal.

    Examples:
        "$2,000.00" -> Decimal("2000.00")
        "2000.00"   -> Decimal("2000.00")
        "18%"       -> Decimal("0.18") when percentage=True
        "18"        -> Decimal("0.18") when percentage=True
        "0.18"      -> Decimal("0.18") when percentage=True
    """
    had_percent = False

    if isinstance(value, Decimal):
        decimal_value = value

    elif isinstance(value, int):
        decimal_value = Decimal(value)

    elif isinstance(value, float):
        decimal_value = Decimal(str(value))

    elif isinstance(value, str):
        cleaned = value.strip()

        if percentage:
            had_percent = "%" in cleaned
            cleaned = cleaned.replace("%", "").strip()

        cleaned = re.sub(
            r"[^0-9.\-]",
            "",
            cleaned,
        )

        if not cleaned:
            raise ValueError(
                f"Cannot normalize numeric value: {value!r}"
            )

        try:
            decimal_value = Decimal(cleaned)
        except InvalidOperation as exc:
            raise ValueError(
                f"Cannot normalize numeric value: {value!r}"
            ) from exc

    else:
        raise TypeError(
            f"Unsupported numeric value type: "
            f"{type(value).__name__}"
        )

    if percentage:
        if had_percent:
            decimal_value /= Decimal("100")

        elif decimal_value > Decimal("1"):
            decimal_value /= Decimal("100")

        if (
            decimal_value < Decimal("0")
            or decimal_value > Decimal("1")
        ):
            raise ValueError(
                f"Percentage value out of range: {value!r}"
            )

    return decimal_value


def normalize_optional_identifier(
    value: Any,
) -> str | None:
    """
    Normalize optional identifier fields returned by an LLM.

    Values representing an explicitly unavailable identifier are
    converted to None.

    Examples:
        None   -> None
        ""     -> None
        "N/A"  -> None
        "NA"   -> None
        "N.A." -> None
        "NONE" -> None
        "NULL" -> None
        "-"    -> None
        "PO-12345" -> "PO-12345"
    """
    if value is None:
        return None

    normalized = str(value).strip()

    if not normalized:
        return None

    if normalized.upper() in {
        "N/A",
        "NA",
        "N.A.",
        "NONE",
        "NULL",
        "-",
    }:
        return None

    return normalized


def normalize_line_item(
    item: dict[str, Any],
) -> ExtractedInvoiceLineItem:
    return ExtractedInvoiceLineItem(
        description=str(
            item["description"]
        ).strip(),
        quantity=int(item["quantity"]),
        unit_price=normalize_decimal(
            item["unit_price"]
        ),
    )


def normalize_extraction_response(
    response_text: str,
) -> ExtractedInvoice:
    """
    Normalize a raw LLM JSON response into the
    ExtractedInvoice schema.

    This function normalizes representation/formatting
    differences but does not invent missing invoice data.
    """
    data = json.loads(response_text)

    if not isinstance(data, dict):
        raise ValueError(
            "LLM response must contain a JSON object."
        )

    required_fields = [
        "invoice_number",
        "vendor",
        "currency",
        "line_items",
        "subtotal",
        "tax_rate",
        "tax",
        "total",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in data
    ]

    if missing_fields:
        raise ValueError(
            "LLM response is missing required fields: "
            + ", ".join(missing_fields)
        )

    normalized_line_items = [
        normalize_line_item(item)
        for item in data["line_items"]
    ]

    return ExtractedInvoice(
        invoice_number=str(
            data["invoice_number"]
        ).strip(),

        vendor=str(
            data["vendor"]
        ).strip(),

        invoice_date=data.get(
            "invoice_date"
        ),

        po_number=normalize_optional_identifier(
            data.get("po_number")
        ),

        currency=str(
            data["currency"]
        ).strip().upper(),

        line_items=normalized_line_items,

        subtotal=normalize_decimal(
            data["subtotal"]
        ),

        tax_rate=normalize_decimal(
            data["tax_rate"],
            percentage=True,
        ),

        tax=normalize_decimal(
            data["tax"]
        ),

        total=normalize_decimal(
            data["total"]
        ),
    )