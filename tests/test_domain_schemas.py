from decimal import Decimal

from app.schemas.invoice import Invoice
from app.schemas.purchase_order import PurchaseOrder


def test_invoice_schema():
    invoice = Invoice(
        invoice_number="INV-001",
        vendor="ABC Supplies",
        po_number="PO-001",
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

    assert invoice.invoice_number == "INV-001"
    assert invoice.currency == "USD"


def test_purchase_order_schema():
    po = PurchaseOrder(
        po_number="PO-001",
        vendor="ABC Supplies",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )

    assert po.po_number == "PO-001"
    assert po.vendor == "ABC Supplies"
    assert po.subtotal == Decimal("2000.00")
    assert po.tax == Decimal("360.00")
    assert po.total == Decimal("2360.00")