from app.schemas.invoice import Invoice
from app.schemas.purchase_order import PurchaseOrder
from app.schemas.vendor import Vendor

from app.erp.repository import ERPRepository


class ERPService:
    """Business operations exposed by the mock ERP."""

    def __init__(self, repository: ERPRepository) -> None:
        self.repository = repository

    def get_vendor(self, vendor_id: str) -> Vendor | None:
        return self.repository.get_vendor(vendor_id)

    def get_purchase_order(
        self,
        po_number: str,
    ) -> PurchaseOrder | None:
        return self.repository.get_purchase_order(po_number)

    def search_purchase_orders_by_vendor(
        self,
        vendor_name: str,
    ) -> list[PurchaseOrder]:
        return self.repository.search_purchase_orders_by_vendor(
            vendor_name
        )

    def check_duplicate_invoice(
        self,
        invoice_number: str,
    ) -> bool:
        return self.repository.is_invoice_settled(
            invoice_number
        )

    def commit_invoice(self, invoice: Invoice) -> str:
        """Settle an invoice in the ERP."""

        if self.check_duplicate_invoice(invoice.invoice_number):
            return "already_settled"

        self.repository.settle_invoice(invoice.invoice_number)

        return "settled"