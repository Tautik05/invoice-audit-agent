from datetime import datetime

from pydantic import BaseModel

from app.schemas.enums import HumanDecision


class HumanReview(BaseModel):
    reviewer_id: str
    decision: HumanDecision
    reason: str | None = None
    reviewed_at: datetime