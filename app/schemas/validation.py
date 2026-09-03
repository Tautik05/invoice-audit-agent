from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.enums import ValidationStatus


class ValidationResult(BaseModel):
    status: ValidationStatus

    calculated_subtotal: Decimal
    calculated_tax: Decimal
    calculated_total: Decimal

    subtotal_valid: bool
    tax_valid: bool
    total_valid: bool
    currency_valid: bool

    errors: list[str] = Field(default_factory=list)