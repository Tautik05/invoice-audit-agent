from decimal import Decimal

from app.reconciliation.engine import reconcile_invoice
from app.schemas.enums import ReconciliationStatus
from app.schemas.invoice import Invoice
from app.schemas.purchase_order import (
    PurchaseOrder,
    PurchaseOrderLineItem,
)
from app.reconciliation.engine import (
    build_ambiguous_result,
)


def make_invoice(
    *,
    vendor="ABC Supplies",
    currency="USD",
    unit_price="200.00",
    total="2360.00",
):
    return Invoice(
        invoice_number="INV-001",
        vendor=vendor,
        invoice_date=None,
        po_number="PO-8821",
        currency=currency,
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal(unit_price),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal(total),
    )


def make_purchase_order(
    *,
    vendor="ABC Supplies",
    currency="USD",
    unit_price="200.00",
    total="2360.00",
):
    return PurchaseOrder(
        po_number="PO-8821",
        vendor=vendor,
        currency=currency,
        line_items=[
            PurchaseOrderLineItem(
                description="Monitor",
                quantity=10,
                unit_price=Decimal(unit_price),
            )
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal(total),
    )


def test_reconcile_matching_invoice():
    invoice = make_invoice()
    purchase_order = make_purchase_order()

    result = reconcile_invoice(
        invoice,
        purchase_order,
    )

    assert result.status == ReconciliationStatus.MATCHED
    assert result.po_found is True
    assert result.vendor_matched is True
    assert result.currency_matched is True
    assert result.line_items_matched is True
    assert result.variance == Decimal("0.00")
    assert result.errors == []


def test_reconcile_vendor_mismatch():
    invoice = make_invoice(vendor="Different Vendor")
    purchase_order = make_purchase_order()

    result = reconcile_invoice(
        invoice,
        purchase_order,
    )

    assert result.status == ReconciliationStatus.VARIANCE
    assert result.vendor_matched is False
    assert result.currency_matched is True
    assert result.line_items_matched is True
    assert result.errors


def test_reconcile_currency_mismatch():
    invoice = make_invoice(currency="EUR")
    purchase_order = make_purchase_order()

    result = reconcile_invoice(
        invoice,
        purchase_order,
    )

    assert result.status == ReconciliationStatus.VARIANCE
    assert result.currency_matched is False


def test_reconcile_line_item_price_mismatch():
    invoice = make_invoice(
        unit_price="220.00",
        total="2596.00",
    )
    purchase_order = make_purchase_order()

    result = reconcile_invoice(
        invoice,
        purchase_order,
    )

    assert result.status == ReconciliationStatus.VARIANCE
    assert result.line_items_matched is False
    assert result.variance == Decimal("236.00")


def test_reconcile_missing_purchase_order():
    invoice = make_invoice()

    result = reconcile_invoice(
        invoice,
        None,
    )

    assert result.status == ReconciliationStatus.NOT_FOUND
    assert result.po_found is False
    assert result.po_total is None
    assert result.variance is None
    assert result.errors

def test_build_ambiguous_result():
    invoice = make_invoice()

    result = build_ambiguous_result(
        invoice,
        candidate_count=3,
    )

    assert result.status == ReconciliationStatus.AMBIGUOUS
    assert result.po_found is False
    assert result.errors