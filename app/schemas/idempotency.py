from datetime import datetime

from pydantic import BaseModel


class IdempotencyRecord(BaseModel):
    idempotency_key: str
    operation: str
    status: str
    response: dict
    created_at: datetime
    completed_at: datetime | None = None