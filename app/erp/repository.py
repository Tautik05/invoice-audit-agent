from decimal import Decimal
import json
import uuid
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
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
from app.db.models.audit_event import AuditEvent as AuditEventModel
from app.schemas.enums import AuditEventType



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

    def add_audit_event(
        self,
        workflow_id: str,
        event_type: str,
        actor: str,
        details: dict | None = None,
        idempotency_key: str | None = None,
    ) -> AuditEventModel | None:
        """Persist an audit event idempotently."""

        if idempotency_key is None:
            idempotency_key = str(uuid.uuid4())

        values = {
            "workflow_id": workflow_id,
            "event_type": event_type,
            "actor": actor,
            "idempotency_key": idempotency_key,
            "details": json.dumps(details) if details is not None else None,
        }

        if self.session.bind is None:
            raise RuntimeError("Session is not bound to a database engine.")

        dialect_name = self.session.bind.dialect.name

        if dialect_name == "postgresql":
            statement = (
                postgres_insert(AuditEventModel)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=[AuditEventModel.idempotency_key],
                )
                .returning(AuditEventModel.id)
            )

            inserted_id = self.session.scalar(statement)

            if inserted_id is None:
                existing_event = self.session.scalar(
                    select(AuditEventModel).where(
                        AuditEventModel.idempotency_key == idempotency_key
                    )
                )

                return existing_event

            audit_event = self.session.get(AuditEventModel, inserted_id)

            if audit_event is None:
                raise RuntimeError(
                    "Audit event was inserted but could not be retrieved."
                )

            return audit_event

        existing_event = self.session.scalar(
            select(AuditEventModel).where(
                AuditEventModel.idempotency_key == idempotency_key
            )
        )

        if existing_event is not None:
            return existing_event

        audit_event = AuditEventModel(**values)
        self.session.add(audit_event)
        self.session.flush()

        return audit_event

    def get_audit_events(
        self,
        workflow_id: str,
    ) -> list[AuditEventModel]:
        """Retrieve audit events for a workflow in chronological order."""

        statement = (
            select(AuditEventModel)
            .where(
                AuditEventModel.workflow_id == workflow_id
            )
            .order_by(
                AuditEventModel.created_at,
                AuditEventModel.id,
            )
        )

        return list(
            self.session.scalars(statement).all()
        )


    def _invoice_matches_existing(
        self,
        invoice: Invoice,
        existing_invoice: InvoiceModel,
    ) -> bool:
        """Check whether an incoming invoice matches the persisted invoice."""

        vendor = self.session.scalar(
            select(VendorModel).where(
                VendorModel.id == existing_invoice.vendor_id
            )
        )

        if vendor is None:
            return False

        if vendor.name.strip().lower() != invoice.vendor.strip().lower():
            return False

        if existing_invoice.po_number != invoice.po_number:
            return False

        if existing_invoice.invoice_date != invoice.invoice_date:
            return False

        if existing_invoice.currency != invoice.currency:
            return False

        if existing_invoice.subtotal != invoice.subtotal:
            return False

        if existing_invoice.tax_rate != invoice.tax_rate:
            return False

        if existing_invoice.tax != invoice.tax:
            return False

        if existing_invoice.total != invoice.total:
            return False

        return True


    def _create_invoice_record(
        self,
        invoice: Invoice,
        vendor: VendorModel,
    ) -> tuple[InvoiceModel | None, bool]:
        """Create an invoice atomically when it does not already exist."""

        values = {
            "invoice_number": invoice.invoice_number,
            "vendor_id": vendor.id,
            "po_number": invoice.po_number,
            "invoice_date": invoice.invoice_date,
            "currency": invoice.currency,
            "subtotal": invoice.subtotal,
            "tax_rate": invoice.tax_rate,
            "tax": invoice.tax,
            "total": invoice.total,
            "status": "settled",
        }

        if self.session.bind is None:
            raise RuntimeError(
                "Session is not bound to a database engine."
            )

        if self.session.bind.dialect.name == "postgresql":
            statement = (
                postgres_insert(InvoiceModel)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=[InvoiceModel.invoice_number],
                )
                .returning(InvoiceModel.id)
            )

            inserted_id = self.session.scalar(statement)

            if inserted_id is None:
                return None, False

            invoice_model = self.session.get(
                InvoiceModel,
                inserted_id,
            )

        else:
            invoice_model = InvoiceModel(**values)
            self.session.add(invoice_model)

            try:
                self.session.flush()
            except Exception:
                raise

        if invoice_model is None:
            raise RuntimeError(
                "Invoice was inserted but could not be retrieved."
            )

        if not invoice_model.id:
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

        return invoice_model, True


    def _record_invoice_settlement(
        self,
        invoice: Invoice,
        workflow_id: str,
        action: str,
    ) -> None:
        """Record a successful invoice settlement."""

        self.add_audit_event(
            workflow_id=workflow_id,
            event_type=AuditEventType.INVOICE_SETTLED.value,
            actor="agent",
            idempotency_key=(
                f"invoice_settled:"
                f"{invoice.invoice_number}"
            ),
            details={
                "invoice_number": invoice.invoice_number,
                "action": action,
                "total": str(invoice.total),
                "currency": invoice.currency,
            },
        )
        
    def settle_invoice(
        self,
        invoice: Invoice,
        workflow_id: str,
    ) -> str:
        """Persist and settle an invoice within the current transaction."""

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
            if not self._invoice_matches_existing(
                invoice,
                existing_invoice,
            ):
                raise ValueError(
                    "Invoice number already exists with different data."
                )

            if existing_invoice.status == "settled":
                return "already_settled"

            existing_invoice.status = "settled"

            if not existing_invoice.line_items:
                for item in invoice.line_items:
                    item_model = InvoiceLineItemModel(
                        invoice_id=existing_invoice.id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                    )
                    self.session.add(item_model)

            self.session.flush()

            self._record_invoice_settlement(
                invoice=invoice,
                workflow_id=workflow_id,
                action="settled_existing_invoice",
            )

            return "settled"

        _, inserted = self._create_invoice_record(
            invoice=invoice,
            vendor=vendor,
        )

        if not inserted:
            existing_invoice = self.session.scalar(
                select(InvoiceModel).where(
                    InvoiceModel.invoice_number
                    == invoice.invoice_number
                )
            )

            if existing_invoice is None:
                raise RuntimeError(
                    "Invoice conflict occurred but existing invoice "
                    "could not be retrieved."
                )

            if not self._invoice_matches_existing(
                invoice,
                existing_invoice,
            ):
                raise ValueError(
                    "Invoice number already exists with different data."
                )

            if existing_invoice.status == "settled":
                return "already_settled"

            existing_invoice.status = "settled"

            if not existing_invoice.line_items:
                for item in invoice.line_items:
                    item_model = InvoiceLineItemModel(
                        invoice_id=existing_invoice.id,
                        description=item.description,
                        quantity=item.quantity,
                        unit_price=item.unit_price,
                    )
                    self.session.add(item_model)

            self.session.flush()

            self._record_invoice_settlement(
                invoice=invoice,
                workflow_id=workflow_id,
                action="settled_existing_invoice",
            )

            return "settled"

        self._record_invoice_settlement(
            invoice=invoice,
            workflow_id=workflow_id,
            action="created_and_settled",
        )

        return "settled"
    
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