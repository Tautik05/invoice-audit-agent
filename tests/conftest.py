from decimal import Decimal

import pytest

from app.erp.repository import ERPRepository
from app.erp.service import ERPService
from app.schemas.purchase_order import (
    PurchaseOrder,
    PurchaseOrderLineItem,
)
from app.schemas.vendor import Vendor


@pytest.fixture
def erp_service() -> ERPService:
    repository = ERPRepository()

    repository.add_vendor(
        Vendor(
            vendor_id="V-001",
            name="ABC Supplies",
            currency="USD",
        )
    )

    repository.add_vendor(
        Vendor(
            vendor_id="V-002",
            name="Acme Corp",
            currency="USD",
        )
    )

    repository.add_purchase_order(
        PurchaseOrder(
            po_number="PO-8821",
            vendor="ABC Supplies",
            currency="USD",
            line_items=[
                PurchaseOrderLineItem(
                    description="Monitor",
                    quantity=10,
                    unit_price=Decimal("200.00"),
                )
            ],
            subtotal=Decimal("2000.00"),
            tax=Decimal("360.00"),
            total=Decimal("2360.00"),
        )
    )

    repository.add_purchase_order(
        PurchaseOrder(
            po_number="PO-9941",
            vendor="Acme Corp",
            currency="USD",
            line_items=[
                PurchaseOrderLineItem(
                    description="Laptop",
                    quantity=5,
                    unit_price=Decimal("800.00"),
                )
            ],
            subtotal=Decimal("4000.00"),
            tax=Decimal("720.00"),
            total=Decimal("4720.00"),
        )
    )

    return ERPService(repository)