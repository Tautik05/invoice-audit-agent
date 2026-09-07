from app.erp.service import ERPService
from app.schemas.purchase_order import PurchaseOrder
from app.schemas.tools import (
    CheckDuplicateInvoiceArgs,
    QueryPurchaseOrderArgs,
    SearchPurchaseOrdersArgs,
)


class ERPTools:
    """Typed operations available to the agent."""

    def __init__(
        self,
        erp_service: ERPService,
    ) -> None:
        self.erp_service = erp_service

    def query_erp_by_po(
        self,
        args: QueryPurchaseOrderArgs,
    ) -> PurchaseOrder | None:
        return self.erp_service.get_purchase_order(
            args.po_number
        )

    def search_erp_by_vendor(
        self,
        args: SearchPurchaseOrdersArgs,
    ) -> list[PurchaseOrder]:
        return self.erp_service.search_purchase_orders_by_vendor(
            args.vendor_name
        )

    def check_duplicate_invoice(
        self,
        args: CheckDuplicateInvoiceArgs,
    ) -> bool:
        return self.erp_service.check_duplicate_invoice(
            args.invoice_number
        )