import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from random import Random
import sys

from faker import Faker

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.schemas.synthetic import (
    SyntheticInvoiceRecord,
    SyntheticLineItem,
)


OUTPUT_PATH = Path("data/synthetic/ground_truth.jsonl")

CURRENCIES = ["USD", "EUR", "GBP", "INR"]

PRODUCTS = [
    "Laptop",
    "Monitor",
    "Keyboard",
    "Mouse",
    "Printer",
    "Office Chair",
    "Desk",
    "Webcam",
    "Headset",
    "Docking Station",
]

TAX_RATES = {
    "USD": Decimal("0.18"),
    "EUR": Decimal("0.20"),
    "GBP": Decimal("0.20"),
    "INR": Decimal("0.18"),
}


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )


def generate_line_items(
    faker: Faker,
    rng: Random,
) -> list[SyntheticLineItem]:
    item_count = rng.randint(1, 5)

    return [
        SyntheticLineItem(
            description=faker.random_element(PRODUCTS),
            quantity=rng.randint(1, 20),
            unit_price=Decimal(
                str(rng.randint(50, 2000))
            ).quantize(Decimal("0.01")),
        )
        for _ in range(item_count)
    ]


def generate_invoice(
    faker: Faker,
    rng: Random,
    invoice_number: int,
) -> SyntheticInvoiceRecord:
    currency = rng.choice(CURRENCIES)

    line_items = generate_line_items(faker, rng)

    subtotal = quantize_money(
        sum(
            (
                item.quantity * item.unit_price
                for item in line_items
            ),
            Decimal("0"),
        )
    )

    tax_rate = TAX_RATES[currency]

    tax = quantize_money(subtotal * tax_rate)
    total = quantize_money(subtotal + tax)

    vendor = faker.company()

    po_number = (
        f"PO-{rng.randint(10000, 99999)}"
        if rng.random() < 0.85
        else None
    )

    return SyntheticInvoiceRecord(
        invoice_number=f"INV-{invoice_number:05d}",
        vendor=vendor,
        invoice_date=faker.date_between(
            start_date="-1y",
            end_date="today",
        ),
        po_number=po_number,
        currency=currency,
        line_items=line_items,
        subtotal=subtotal,
        tax_rate=tax_rate,
        tax=tax,
        total=total,
    )


def generate_dataset(
    count: int = 100,
    seed: int = 42,
) -> None:
    faker = Faker()
    faker.seed_instance(seed)

    rng = Random(seed)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        for index in range(1, count + 1):
            invoice = generate_invoice(
                faker=faker,
                rng=rng,
                invoice_number=index,
            )

            file.write(
                json.dumps(
                    invoice.model_dump(mode="json")
                )
                + "\n"
            )


if __name__ == "__main__":
    generate_dataset()
    print(f"Generated dataset: {OUTPUT_PATH}")