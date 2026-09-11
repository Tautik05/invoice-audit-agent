from collections.abc import Callable

from sqlalchemy.orm import Session

from app.erp.repository import ERPRepository
from app.erp.unit_of_work import ERPUnitOfWork
from app.schemas.invoice import Invoice
from app.schemas.purchase_order import PurchaseOrder
from app.schemas.vendor import Vendor


class ERPService:
    """Business operations exposed by the mock ERP."""

    def __init__(
        self,
        repository: ERPRepository | None = None,
        session_factory: Callable[[], Session] | None = None,
    ) -> None:
        if repository is None and session_factory is None:
            raise ValueError(
                "Either repository or session_factory must be provided."
            )

        if repository is not None and session_factory is not None:
            raise ValueError(
                "Provide either repository or session_factory, not both."
            )

        self.repository = repository
        self.session_factory = session_factory

    @classmethod
    def from_session_factory(
        cls,
        session_factory: Callable[[], Session],
    ) -> "ERPService":
        """Create an ERP service that opens a session per operation."""

        return cls(
            session_factory=session_factory,
        )

    def get_vendor(
        self,
        vendor_id: str,
    ) -> Vendor | None:
        if self.repository is not None:
            return self.repository.get_vendor(vendor_id)

        with ERPUnitOfWork(self.session_factory) as uow:
            return uow.repository.get_vendor(vendor_id)

    def get_purchase_order(
        self,
        po_number: str,
    ) -> PurchaseOrder | None:
        if self.repository is not None:
            return self.repository.get_purchase_order(po_number)

        with ERPUnitOfWork(self.session_factory) as uow:
            return uow.repository.get_purchase_order(po_number)

    def search_purchase_orders_by_vendor(
        self,
        vendor_name: str,
    ) -> list[PurchaseOrder]:
        if self.repository is not None:
            return self.repository.search_purchase_orders_by_vendor(
                vendor_name
            )

        with ERPUnitOfWork(self.session_factory) as uow:
            return uow.repository.search_purchase_orders_by_vendor(
                vendor_name
            )

    def check_duplicate_invoice(
        self,
        invoice_number: str,
    ) -> bool:
        if self.repository is not None:
            return self.repository.is_invoice_settled(
                invoice_number
            )

        with ERPUnitOfWork(self.session_factory) as uow:
            return uow.repository.is_invoice_settled(
                invoice_number
            )

    def settle_invoice(
        self,
        invoice: Invoice,
        workflow_id: str,
    ) -> str:
        """Persist and settle an invoice."""

        if self.repository is not None:
            return self.repository.settle_invoice(
                invoice=invoice,
                workflow_id=workflow_id,
            )

        with ERPUnitOfWork(self.session_factory) as uow:
            result = uow.repository.settle_invoice(
                invoice=invoice,
                workflow_id=workflow_id,
            )
            uow.commit()
            return result