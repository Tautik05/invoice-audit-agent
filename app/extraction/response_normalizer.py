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

    Examples:
        "$2,000.00" -> Decimal("2000.00")
        "2000.00"   -> Decimal("2000.00")
        "18%"       -> Decimal("0.18") when percentage=True
    """

    if isinstance(value, Decimal):
        decimal_value = value

    elif isinstance(value, int):
        decimal_value = Decimal(value)

    elif isinstance(value, float):
        decimal_value = Decimal(str(value))

    elif isinstance(value, str):
        cleaned = value.strip()

        if percentage:
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

        if percentage and "%" in value:
            decimal_value /= Decimal("100")

    else:
        raise TypeError(
            f"Unsupported numeric value type: "
            f"{type(value).__name__}"
        )

    return decimal_value


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
        po_number=(
            str(data["po_number"]).strip()
            if data.get("po_number") is not None
            else None
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