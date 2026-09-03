from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class InvoiceLineItem(BaseModel):
    description: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class Invoice(BaseModel):
    invoice_number: str
    vendor: str
    invoice_date: date | None = None
    po_number: str | None = None

    currency: str

    line_items: list[InvoiceLineItem]

    subtotal: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)