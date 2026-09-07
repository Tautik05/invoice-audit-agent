from decimal import Decimal

from pydantic import BaseModel, Field


class PurchaseOrderLineItem(BaseModel):
    description: str = Field(min_length=1)
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)


class PurchaseOrder(BaseModel):
    po_number: str = Field(min_length=1)
    vendor: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)
    line_items: list[PurchaseOrderLineItem] = Field(min_length=1)
    subtotal: Decimal = Field(ge=0)
    tax_rate: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)