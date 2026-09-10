from pydantic import BaseModel, Field


class QueryPurchaseOrderArgs(BaseModel):
    po_number: str = Field(min_length=1)


class SearchPurchaseOrdersArgs(BaseModel):
    vendor_name: str = Field(min_length=1)


class CheckDuplicateInvoiceArgs(BaseModel):
    invoice_number: str = Field(min_length=1)


class SettleInvoiceArgs(BaseModel):
    invoice_number: str = Field(min_length=1)
    workflow_id: str = Field(min_length=1)