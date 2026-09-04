from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class SyntheticLineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class SyntheticInvoiceRecord(BaseModel):
    invoice_number: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    invoice_date: date
    po_number: str | None = None
    currency: str = Field(min_length=3, max_length=3)

    line_items: list[SyntheticLineItem] = Field(min_length=1)

    subtotal: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)