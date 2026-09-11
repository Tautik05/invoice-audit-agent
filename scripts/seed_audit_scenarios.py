import json
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

# ---------------------------------------------------------------------------
# Project import setup
# ---------------------------------------------------------------------------

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.db.models.invoice import Invoice
from app.db.models.purchase_order import PurchaseOrder
from app.db.models.purchase_order_item import PurchaseOrderItem
from app.db.models.vendor import Vendor
from app.db.session import SessionLocal


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURE_PATH = Path(
    "data/audit_scenarios/erp_fixtures.json"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_fixtures() -> dict:
    """Load ERP fixture data."""

    if not FIXTURE_PATH.exists():
        raise FileNotFoundError(
            f"ERP fixture file not found: {FIXTURE_PATH}"
        )

    with FIXTURE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def seed_vendor(
    session,
    fixture: dict,
) -> Vendor:
    """Create a vendor if it does not already exist."""

    vendor = session.scalar(
        select(Vendor).where(
            Vendor.vendor_code
            == fixture["vendor_code"]
        )
    )

    if vendor is None:
        vendor = Vendor(
            vendor_code=fixture["vendor_code"],
            name=fixture["name"],
            currency=fixture["currency"],
        )

        session.add(vendor)
        session.flush()

        print(
            f"  + Vendor: "
            f"{fixture['vendor_code']} "
            f"({fixture['name']})"
        )

    else:
        print(
            f"  = Vendor exists: "
            f"{fixture['vendor_code']} "
            f"({fixture['name']})"
        )

    return vendor


def seed_purchase_order(
    session,
    fixture: dict,
    vendors_by_code: dict[str, Vendor],
) -> PurchaseOrder:
    """Create a purchase order if it does not already exist."""

    po_number = fixture["po_number"]

    existing_po = session.scalar(
        select(PurchaseOrder).where(
            PurchaseOrder.po_number == po_number
        )
    )

    if existing_po is not None:
        print(
            f"  = PO exists: {po_number}"
        )
        return existing_po

    vendor_code = fixture["vendor_code"]

    vendor = vendors_by_code.get(
        vendor_code
    )

    if vendor is None:
        raise ValueError(
            f"Vendor {vendor_code} not found "
            f"for PO {po_number}."
        )

    purchase_order = PurchaseOrder(
        po_number=po_number,
        vendor_id=vendor.id,
        currency=fixture["currency"],
        tax_rate=Decimal(
            fixture["tax_rate"]
        ),
        status=fixture["status"],
    )

    session.add(purchase_order)
    session.flush()

    for item in fixture["line_items"]:
        purchase_order_item = PurchaseOrderItem(
            purchase_order_id=purchase_order.id,
            description=item["description"],
            quantity=item["quantity"],
            unit_price=Decimal(
                item["unit_price"]
            ),
        )

        session.add(
            purchase_order_item
        )

    session.flush()

    print(
        f"  + PO: {po_number} "
        f"({vendor.name})"
    )

    return purchase_order


def seed_settled_invoice(
    session,
    fixture: dict,
    vendors_by_code: dict[str, Vendor],
) -> Invoice:
    """Create the pre-existing settled invoice if necessary."""

    invoice_number = fixture[
        "invoice_number"
    ]

    existing_invoice = session.scalar(
        select(Invoice).where(
            Invoice.invoice_number
            == invoice_number
        )
    )

    if existing_invoice is not None:
        print(
            f"  = Settled invoice exists: "
            f"{invoice_number}"
        )
        return existing_invoice

    vendor = vendors_by_code.get(
        fixture["vendor_code"]
    )

    if vendor is None:
        raise ValueError(
            f"Vendor "
            f"{fixture['vendor_code']} "
            f"not found for invoice "
            f"{invoice_number}."
        )

    # The duplicate scenario only needs the invoice
    # to exist in the ERP as settled.
    #
    # Financial fields are intentionally populated
    # with the same values as the corresponding PDF.
    if invoice_number == "AUDIT-007":
        subtotal = Decimal("6000.00")
        tax_rate = Decimal("0.18")
        tax = Decimal("1080.00")
        total = Decimal("7080.00")
        invoice_date = "2026-09-07"

    else:
        raise ValueError(
            f"Unsupported settled invoice fixture: "
            f"{invoice_number}"
        )

    invoice = Invoice(
        invoice_number=invoice_number,
        vendor_id=vendor.id,
        po_number=fixture["po_number"],
        invoice_date=invoice_date,
        currency=fixture["currency"],
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax=tax,
        total=total,
        status="settled",
    )

    session.add(invoice)
    session.flush()

    print(
        f"  + Settled invoice: "
        f"{invoice_number}"
    )

    return invoice


# ---------------------------------------------------------------------------
# Main seeding logic
# ---------------------------------------------------------------------------

def seed_audit_scenarios() -> None:
    """Seed ERP state required by the audit scenario dataset."""

    fixtures = load_fixtures()

    print(
        "Seeding audit scenario ERP fixtures..."
    )

    with SessionLocal() as session:

        # ---------------------------------------------------------------
        # Vendors
        # ---------------------------------------------------------------

        print("\nVendors:")

        vendors_by_code = {}

        for vendor_fixture in fixtures[
            "vendors"
        ]:
            vendor = seed_vendor(
                session,
                vendor_fixture,
            )

            vendors_by_code[
                vendor.vendor_code
            ] = vendor

        # ---------------------------------------------------------------
        # Purchase orders
        # ---------------------------------------------------------------

        print("\nPurchase Orders:")

        for po_fixture in fixtures[
            "purchase_orders"
        ]:
            seed_purchase_order(
                session,
                po_fixture,
                vendors_by_code,
            )

        # ---------------------------------------------------------------
        # Existing settled invoices
        # ---------------------------------------------------------------

        print("\nSettled Invoices:")

        for invoice_fixture in fixtures[
            "settled_invoices"
        ]:
            seed_settled_invoice(
                session,
                invoice_fixture,
                vendors_by_code,
            )

        session.commit()

    print(
        "\nAudit scenario ERP fixtures "
        "seeded successfully."
    )


if __name__ == "__main__":
    seed_audit_scenarios()