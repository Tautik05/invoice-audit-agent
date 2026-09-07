from decimal import Decimal

from app.erp.unit_of_work import ERPUnitOfWork
from app.schemas.invoice import Invoice


def test_settled_invoice_persists_across_sessions(
    session_factory,
    seeded_database,
):
    invoice = Invoice(
        invoice_number="INV-PERSIST-001",
        vendor="ABC Supplies",
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        uow.repository.settle_invoice(invoice)
        uow.commit()

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        assert (
            uow.repository.is_invoice_settled(
                "INV-PERSIST-001"
            )
            is True
        )


def test_invoice_rollback_removes_uncommitted_changes(
    session_factory,
    seeded_database,
):
    invoice = Invoice(
        invoice_number="INV-ROLLBACK-001",
        vendor="ABC Supplies",
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 1,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("200.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("36.00"),
        total=Decimal("236.00"),
    )

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        uow.repository.settle_invoice(invoice)
        uow.rollback()

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        assert (
            uow.repository.is_invoice_settled(
                "INV-ROLLBACK-001"
            )
            is False
        )