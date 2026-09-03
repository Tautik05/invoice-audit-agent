from app.schemas.purchase_order import PurchaseOrder
from app.schemas.vendor import Vendor


class ERPRepository:
    """In-memory repository representing our mock ERP database."""

    def __init__(self) -> None:
        self._vendors: dict[str, Vendor] = {}
        self._purchase_orders: dict[str, PurchaseOrder] = {}
        self._settled_invoices: set[str] = set()

    def add_vendor(self, vendor: Vendor) -> None:
        self._vendors[vendor.vendor_id] = vendor

    def add_purchase_order(self, purchase_order: PurchaseOrder) -> None:
        self._purchase_orders[purchase_order.po_number] = purchase_order

    def get_vendor(self, vendor_id: str) -> Vendor | None:
        return self._vendors.get(vendor_id)

    def get_purchase_order(
        self,
        po_number: str,
    ) -> PurchaseOrder | None:
        return self._purchase_orders.get(po_number)

    def search_purchase_orders_by_vendor(
        self,
        vendor_name: str,
    ) -> list[PurchaseOrder]:
        vendor_name = vendor_name.lower()

        return [
            po
            for po in self._purchase_orders.values()
            if po.vendor.lower() == vendor_name
        ]

    def is_invoice_settled(self, invoice_number: str) -> bool:
        return invoice_number in self._settled_invoices

    def settle_invoice(self, invoice_number: str) -> None:
        self._settled_invoices.add(invoice_number)