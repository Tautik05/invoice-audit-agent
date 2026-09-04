from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ExtractedInvoiceLineItem(BaseModel):
    description: str
    quantity: int
    unit_price: Decimal


class ExtractedInvoice(BaseModel):
    invoice_number: str
    vendor: str
    invoice_date: date | None = None
    po_number: str | None = None
    currency: str

    line_items: list[ExtractedInvoiceLineItem]

    subtotal: Decimal
    tax_rate: Decimal
    tax: Decimal
    total: Decimal