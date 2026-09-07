import json
import sys
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.db.models.purchase_order import PurchaseOrder
from app.db.models.purchase_order_item import PurchaseOrderItem
from app.db.models.vendor import Vendor
from app.db.session import SessionLocal


GROUND_TRUTH_PATH = Path(
    "data/synthetic/ground_truth.jsonl"
)

SEED_COUNT = 10


def load_ground_truth() -> list[dict]:
    if not GROUND_TRUTH_PATH.exists():
        raise FileNotFoundError(
            f"Ground truth not found: "
            f"{GROUND_TRUTH_PATH}"
        )

    records: list[dict] = []

    with GROUND_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            records.append(json.loads(line))

    return records


def select_seed_records(
    records: list[dict],
) -> list[dict]:
    records_with_po = [
        record
        for record in records
        if record.get("po_number")
    ]

    if len(records_with_po) < SEED_COUNT:
        raise ValueError(
            f"Need at least {SEED_COUNT} records "
            f"with purchase orders, found "
            f"{len(records_with_po)}."
        )

    return records_with_po[:SEED_COUNT]


def seed_erp() -> None:
    records = load_ground_truth()
    seed_records = select_seed_records(records)

    created_vendors = 0
    created_purchase_orders = 0
    created_items = 0

    with SessionLocal() as session:
        for record in seed_records:
            po_number = record["po_number"]
            invoice_number = record["invoice_number"]

            vendor_code = (
                f"V-{invoice_number.removeprefix('INV-')}"
            )

            vendor = session.scalar(
                select(Vendor).where(
                    Vendor.vendor_code == vendor_code
                )
            )

            if vendor is None:
                vendor = Vendor(
                    vendor_code=vendor_code,
                    name=record["vendor"],
                    currency=record["currency"],
                )

                session.add(vendor)
                session.flush()

                created_vendors += 1

            purchase_order = session.scalar(
                select(PurchaseOrder).where(
                    PurchaseOrder.po_number == po_number
                )
            )

            if purchase_order is not None:
                continue

            purchase_order = PurchaseOrder(
                po_number=po_number,
                vendor_id=vendor.id,
                currency=record["currency"],
                tzx_rate=Decimal(str(record["tzx_rate"])),
                status="approved",
            )

            session.add(purchase_order)
            session.flush()

            created_purchase_orders += 1

            for item in record["line_items"]:
                purchase_order_item = PurchaseOrderItem(
                    purchase_order_id=purchase_order.id,
                    description=item["description"],
                    quantity=item["quantity"],
                    unit_price=Decimal(
                        str(item["unit_price"])
                    ),
                )

                session.add(purchase_order_item)
                created_items += 1

        session.commit()

    print("ERP seed completed.")
    print(f"Seed records selected: {len(seed_records)}")
    print(f"Vendors created: {created_vendors}")
    print(
        "Purchase orders created: "
        f"{created_purchase_orders}"
    )
    print(
        "Purchase order items created: "
        f"{created_items}"
    )


if __name__ == "__main__":
    seed_erp()