from pydantic import BaseModel, Field


class Vendor(BaseModel):
    vendor_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    currency: str = Field(min_length=3, max_length=3)