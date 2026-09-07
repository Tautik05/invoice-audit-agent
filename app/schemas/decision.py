from pydantic import BaseModel, Field

from app.schemas.enums import DecisionAction


class DecisionResult(BaseModel):
    """Result of the invoice workflow decision engine."""

    action: DecisionAction
    reasons: list[str] = Field(
        default_factory=list
    )