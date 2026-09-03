from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.enums import ReconciliationStatus


class ReconciliationResult(BaseModel):
    status: ReconciliationStatus

    po_found: bool
    vendor_matched: bool
    currency_matched: bool
    line_items_matched: bool

    invoice_total: Decimal
    po_total: Decimal | None = None
    variance: Decimal | None = None

    errors: list[str] = Field(default_factory=list)