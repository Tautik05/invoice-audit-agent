from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice as InvoiceModel
from app.db.models.invoice_line_item import (
    InvoiceLineItem as InvoiceLineItemModel,
)
from app.db.models.purchase_order import (
    PurchaseOrder as PurchaseOrderModel,
)
from app.db.models.purchase_order_item import (
    PurchaseOrderItem as PurchaseOrderItemModel,
)
from app.db.models.vendor import Vendor as VendorModel
from app.schemas.invoice import Invoice
from app.schemas.purchase_order import (
    PurchaseOrder,
    PurchaseOrderLineItem,
)
from app.schemas.vendor import Vendor


class ERPRepository:
    """Persistence layer for ERP data backed by SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def add_vendor(self, vendor: Vendor) -> None:
        """Persist a vendor if it does not already exist."""
        existing_vendor = self.session.scalar(
            select(VendorModel).where(
                VendorModel.vendor_code == vendor.vendor_id
            )
        )

        if existing_vendor is not None:
            return

        vendor_model = VendorModel(
            vendor_code=vendor.vendor_id,
            name=vendor.name,
            currency=vendor.currency,
        )

        self.session.add(vendor_model)
        self.session.flush()

    def add_purchase_order(
        self,
        purchase_order: PurchaseOrder,
    ) -> None:
        """Persist a purchase order and its line items."""
        existing_po = self.session.scalar(
            select(PurchaseOrderModel).where(
                PurchaseOrderModel.po_number
                == purchase_order.po_number
            )
        )

        if existing_po is not None:
            return

        vendor = self.session.scalar(
            select(VendorModel).where(
                VendorModel.name == purchase_order.vendor
            )
        )

        if vendor is None:
            raise ValueError(
                f"Vendor not found: {purchase_order.vendor}"
            )

        purchase_order_model = PurchaseOrderModel(
            po_number=purchase_order.po_number,
            vendor_id=vendor.id,
            currency=purchase_order.currency,
            tax_rate=purchase_order.tax_rate,
            status="approved",
        )

        self.session.add(purchase_order_model)
        self.session.flush()

        for item in purchase_order.line_items:
            item_model = PurchaseOrderItemModel(
                purchase_order_id=purchase_order_model.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )

            self.session.add(item_model)

        self.session.flush()

    def get_vendor(
        self,
        vendor_id: str,
    ) -> Vendor | None:
        """Retrieve a vendor by vendor code."""
        vendor_model = self.session.scalar(
            select(VendorModel).where(
                VendorModel.vendor_code == vendor_id
            )
        )

        if vendor_model is None:
            return None

        return Vendor(
            vendor_id=vendor_model.vendor_code,
            name=vendor_model.name,
            currency=vendor_model.currency,
        )

    def get_purchase_order(
        self,
        po_number: str,
    ) -> PurchaseOrder | None:
        """Retrieve a purchase order by PO number."""
        purchase_order_model = self.session.scalar(
            select(PurchaseOrderModel).where(
                PurchaseOrderModel.po_number == po_number
            )
        )

        if purchase_order_model is None:
            return None

        return self._to_domain_purchase_order(
            purchase_order_model
        )

    def search_purchase_orders_by_vendor(
        self,
        vendor_name: str,
    ) -> list[PurchaseOrder]:
        """Retrieve purchase orders belonging to a vendor."""
        statement = (
            select(PurchaseOrderModel)
            .join(PurchaseOrderModel.vendor)
            .where(VendorModel.name.ilike(vendor_name))
        )

        purchase_orders = self.session.scalars(
            statement
        ).all()

        return [
            self._to_domain_purchase_order(po)
            for po in purchase_orders
        ]

    def is_invoice_settled(
        self,
        invoice_number: str,
    ) -> bool:
        """Check whether an invoice has already been settled."""
        invoice = self.session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number == invoice_number
            )
        )

        return (
            invoice is not None
            and invoice.status == "settled"
        )

    def settle_invoice(
        self,
        invoice: Invoice,
    ) -> None:
        """Persist an invoice and mark it as settled."""
        vendor = self.session.scalar(
            select(VendorModel).where(
                VendorModel.name == invoice.vendor
            )
        )

        if vendor is None:
            raise ValueError(
                f"Vendor not found: {invoice.vendor}"
            )

        existing_invoice = self.session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == invoice.invoice_number
            )
        )

        if existing_invoice is not None:
            if existing_invoice.status == "settled":
                return

            existing_invoice.status = "settled"
            self.session.flush()
            return

        invoice_model = InvoiceModel(
            invoice_number=invoice.invoice_number,
            vendor_id=vendor.id,
            po_number=invoice.po_number,
            invoice_date=invoice.invoice_date,
            currency=invoice.currency,
            subtotal=invoice.subtotal,
            tax_rate=invoice.tax_rate,
            tax=invoice.tax,
            total=invoice.total,
            status="settled",
        )

        self.session.add(invoice_model)
        self.session.flush()

        for item in invoice.line_items:
            item_model = InvoiceLineItemModel(
                invoice_id=invoice_model.id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )

            self.session.add(item_model)

        self.session.flush()

    @staticmethod
    def _to_domain_purchase_order(
        purchase_order_model: PurchaseOrderModel,
    ) -> PurchaseOrder:
        """Convert an ORM purchase order into a domain model."""
        line_items = [
            PurchaseOrderLineItem(
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in purchase_order_model.items
        ]

        subtotal = sum(
            (
                item.quantity * item.unit_price
                for item in line_items
            ),
            Decimal("0.00"),
        )

        tax = (
            subtotal * purchase_order_model.tax_rate
        ).quantize(Decimal("0.01"))

        total = subtotal + tax

        return PurchaseOrder(
            po_number=purchase_order_model.po_number,
            vendor=purchase_order_model.vendor.name,
            currency=purchase_order_model.currency,
            line_items=line_items,
            subtotal=subtotal,
            tax_rate=purchase_order_model.tax_rate,
            tax=tax,
            total=total,
        )