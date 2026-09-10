from decimal import Decimal
import pytest
import threading
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from app.erp.repository import ERPRepository
from app.erp.unit_of_work import ERPUnitOfWork
from app.schemas.invoice import Invoice
from sqlalchemy import select
from app.db.models.audit_event import AuditEvent
from app.db.models.invoice import Invoice as InvoiceModel
from app.db.models.vendor import Vendor as VendorModel

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

        uow.repository.settle_invoice(
            invoice,
            workflow_id="test-workflow-persist-001",
        )
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

        uow.repository.settle_invoice(
            invoice,
            workflow_id="test-workflow-rollback-001",
        )
        uow.rollback()

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        assert (
            uow.repository.is_invoice_settled(
                "INV-ROLLBACK-001"
            )
            is False
        )

def test_settlement_and_audit_rollback_together(
    session_factory,
    seeded_database,
):
    invoice = Invoice(
        invoice_number="INV-AUDIT-ROLLBACK-001",
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

    workflow_id = "test-workflow-audit-rollback-001"

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        result = uow.repository.settle_invoice(
            invoice,
            workflow_id=workflow_id,
        )

        assert result == "settled"

        uow.rollback()

    with session_factory() as session:
        persisted_invoice = session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == "INV-AUDIT-ROLLBACK-001"
            )
        )

        audit_event = session.scalar(
            select(AuditEvent).where(
                AuditEvent.workflow_id == workflow_id
            )
        )

        assert persisted_invoice is None
        assert audit_event is None

def test_settlement_creates_audit_event(
    session_factory,
    seeded_database,
):
    invoice = Invoice(
        invoice_number="INV-AUDIT-001",
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

        result = uow.repository.settle_invoice(
            invoice,
            workflow_id="test-workflow-audit-001",
        )

        assert result == "settled"

        uow.commit()

    with session_factory() as session:
        audit_event = session.scalar(
            select(AuditEvent).where(
                AuditEvent.workflow_id == "test-workflow-audit-001"
            )
        )

        assert audit_event is not None
        assert audit_event.event_type == "invoice_settled"
        assert audit_event.actor == "agent"
        assert audit_event.details is not None

def test_settlement_rolls_back_when_audit_fails(
    session_factory,
    seeded_database,
    monkeypatch,
):
    invoice = Invoice(
        invoice_number="INV-AUDIT-FAIL-001",
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

    workflow_id = "test-workflow-audit-fail-001"

    def failing_audit_event(
        self,
        workflow_id,
        event_type,
        actor,
        details=None,
        idempotency_key=None,
    ):
        raise RuntimeError("Audit persistence failed.")

    monkeypatch.setattr(
        ERPRepository,
        "add_audit_event",
        failing_audit_event,
    )

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        with pytest.raises(RuntimeError, match="Audit persistence failed"):
            uow.repository.settle_invoice(
                invoice,
                workflow_id=workflow_id,
            )

        uow.rollback()

    with session_factory() as session:
        persisted_invoice = session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == "INV-AUDIT-FAIL-001"
            )
        )

        audit_event = session.scalar(
            select(AuditEvent).where(
                AuditEvent.workflow_id == workflow_id
            )
        )

        assert persisted_invoice is None
        assert audit_event is None


def test_existing_received_invoice_can_be_settled(
    session_factory,
    seeded_database,
):
    invoice = Invoice(
        invoice_number="INV-EXISTING-001",
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

        # Create the invoice in a non-settled state.
        vendor = uow.repository.session.scalar(
            select(VendorModel).where(
                VendorModel.name == "ABC Supplies"
            )
        )

        assert vendor is not None

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
            status="received",
        )

        uow.repository.session.add(invoice_model)
        uow.repository.session.flush()

        uow.commit()

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        result = uow.repository.settle_invoice(
            invoice,
            workflow_id="test-workflow-existing-001",
        )

        assert result == "settled"

        uow.commit()

    with session_factory() as session:
        persisted_invoice = session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == invoice.invoice_number
            )
        )

        assert persisted_invoice is not None
        assert persisted_invoice.status == "settled"



def test_same_invoice_number_with_different_data_is_rejected(
    session_factory,
    seeded_database,
):
    """Reject reuse of an invoice number with different financial data."""

    original_invoice = Invoice(
        invoice_number="INV-CONFLICT-001",
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

    conflicting_invoice = Invoice(
        invoice_number="INV-CONFLICT-001",
        vendor="ABC Supplies",
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 2,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("400.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("72.00"),
        total=Decimal("472.00"),
    )

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        result = uow.repository.settle_invoice(
            original_invoice,
            workflow_id="workflow-conflict-original",
        )

        assert result == "settled"

        uow.commit()

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        with pytest.raises(
            ValueError,
            match="Invoice number already exists with different data",
        ):
            uow.repository.settle_invoice(
                conflicting_invoice,
                workflow_id="workflow-conflict-different",
            )

        uow.rollback()

    with session_factory() as session:
        persisted_invoice = session.scalar(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == "INV-CONFLICT-001"
            )
        )

    assert persisted_invoice is not None
    assert persisted_invoice.status == "settled"
    assert persisted_invoice.total == Decimal("236.00")


def test_settling_same_invoice_twice_is_idempotent(
    session_factory,
    seeded_database,
):
    """Settling the same invoice twice must not duplicate the settlement."""

    invoice = Invoice(
        invoice_number="INV-IDEMPOTENT-001",
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

        first_result = uow.repository.settle_invoice(
            invoice,
            workflow_id="workflow-idempotent-001",
        )

        assert first_result == "settled"

        uow.commit()

    with ERPUnitOfWork(session_factory) as uow:
        assert uow.repository is not None

        second_result = uow.repository.settle_invoice(
            invoice,
            workflow_id="workflow-idempotent-002",
        )

        assert second_result == "already_settled"

        uow.commit()

    with session_factory() as session:
        invoices = session.scalars(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == "INV-IDEMPOTENT-001"
            )
        ).all()

        audit_events = session.scalars(
            select(AuditEvent).where(
                AuditEvent.event_type == "invoice_settled"
            )
        ).all()

    assert len(invoices) == 1
    assert len(audit_events) == 1

def test_concurrent_settlement_allows_only_one_invoice(
    postgres_session_factory,
    seeded_postgres_database,
    monkeypatch,
):
    """Verify concurrent settlement creates one invoice and one audit event."""

    invoice = Invoice(
        invoice_number="INV-CONCURRENCY-001",
        vendor="ABC Supplies",
        po_number="PO-CONCURRENCY-001",
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

    barrier = Barrier(2)

    original_create_invoice_record = (
        ERPRepository._create_invoice_record
    )

    def synchronized_create_invoice_record(
        self,
        invoice,
        vendor,
    ):
        barrier.wait()

        return original_create_invoice_record(
            self,
            invoice,
            vendor,
        )

    monkeypatch.setattr(
        ERPRepository,
        "_create_invoice_record",
        synchronized_create_invoice_record,
    )

    def settle() -> str:
        with ERPUnitOfWork(
            postgres_session_factory
        ) as uow:
            assert uow.repository is not None

            result = uow.repository.settle_invoice(
                invoice,
                workflow_id="workflow-concurrency-001",
            )

            uow.commit()

            return result

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(settle)
            for _ in range(2)
        ]

        results = [
            future.result()
            for future in futures
        ]

    with postgres_session_factory() as session:
        invoices = session.scalars(
            select(InvoiceModel).where(
                InvoiceModel.invoice_number
                == "INV-CONCURRENCY-001"
            )
        ).all()

        audit_events = session.scalars(
            select(AuditEvent).where(
                AuditEvent.workflow_id
                == "workflow-concurrency-001"
            )
        ).all()

    assert len(invoices) == 1
    assert invoices[0].status == "settled"

    assert len(audit_events) == 1

    assert sorted(results) == [
        "already_settled",
        "settled",
    ]