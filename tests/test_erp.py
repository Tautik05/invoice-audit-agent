from decimal import Decimal

from app.schemas.invoice import Invoice
from sqlalchemy import func, select
from app.db.models.audit_event import AuditEvent

def test_get_purchase_order(erp_service):
    po = erp_service.get_purchase_order("PO-8821")

    assert po is not None
    assert po.vendor == "ABC Supplies"
    assert po.total == Decimal("2360.00")


def test_get_missing_purchase_order(erp_service):
    po = erp_service.get_purchase_order("PO-9999")

    assert po is None


def test_search_purchase_orders_by_vendor(erp_service):
    results = erp_service.search_purchase_orders_by_vendor(
        "ABC Supplies"
    )

    assert len(results) == 1
    assert results[0].po_number == "PO-8821"


def test_duplicate_invoice_detection(erp_service):
    invoice = Invoice(
        invoice_number="INV-001",
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

    assert erp_service.check_duplicate_invoice(
        "INV-001"
    ) is False

    result = erp_service.settle_invoice(
        invoice,
        workflow_id="test-workflow-001",
    )
    assert result == "settled"

    assert erp_service.check_duplicate_invoice(
        "INV-001"
    ) is True


def test_duplicate_commit_is_idempotent(
    erp_service,
    session_factory,
):
    invoice = Invoice(
        invoice_number="INV-002",
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

    first_result = erp_service.settle_invoice(
        invoice,
        workflow_id="test-workflow-002",
    )

    second_result = erp_service.settle_invoice(
        invoice,
        workflow_id="test-workflow-002",
    )

    with session_factory() as session:
        audit_count = session.scalar(
            select(func.count(AuditEvent.id)).where(
                AuditEvent.workflow_id == "test-workflow-002"
            )
        )

    assert audit_count == 1
    assert first_result == "settled"
    assert second_result == "already_settled"