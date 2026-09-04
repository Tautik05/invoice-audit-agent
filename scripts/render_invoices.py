import json
from pathlib import Path
import sys
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)
from app.schemas.synthetic import SyntheticInvoiceRecord
from app.synthetic.rendering import InvoiceRenderer


GROUND_TRUTH_PATH = Path(
    "data/synthetic/ground_truth.jsonl"
)


def load_invoices() -> list[SyntheticInvoiceRecord]:
    invoices = []

    with GROUND_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        for line in file:
            data = json.loads(line)
            invoices.append(
                SyntheticInvoiceRecord.model_validate(data)
            )

    return invoices


def main() -> None:
    invoices = load_invoices()

    renderer = InvoiceRenderer()

    for invoice in invoices:
        output_path = renderer.render(invoice)
        print(f"Rendered: {output_path}")


if __name__ == "__main__":
    main()