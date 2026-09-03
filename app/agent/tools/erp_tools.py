from app.erp.service import ERPService


class ERPTools:
    """Typed operations available to the agent."""

    def __init__(self, erp_service: ERPService) -> None:
        self.erp_service = erp_service

    def query_erp_by_po(self, po_number: str):
        return self.erp_service.get_purchase_order(po_number)

    def search_erp_by_vendor(self, vendor_name: str):
        return self.erp_service.search_purchase_orders_by_vendor(
            vendor_name
        )

    def check_duplicate_invoice(self, invoice_number: str) -> bool:
        return self.erp_service.check_duplicate_invoice(
            invoice_number
        )