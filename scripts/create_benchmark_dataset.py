import json
import sys
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.schemas.synthetic import SyntheticInvoiceRecord
from app.synthetic.corruption import (
    CorruptionType,
    corrupt_currency,
    corrupt_subtotal,
    corrupt_tax,
    corrupt_total,
    remove_po,
)
from app.synthetic.rendering import InvoiceRenderer


GROUND_TRUTH_PATH = Path(
    "data/synthetic/ground_truth.jsonl"
)

OUTPUT_DIRECTORY = Path(
    "data/benchmark/documents"
)

BENCHMARK_GROUND_TRUTH_PATH = Path(
    "data/benchmark/ground_truth.jsonl"
)

MANIFEST_PATH = Path(
    "data/benchmark/evaluation_set.json"
)


def load_invoices() -> dict[
    str,
    SyntheticInvoiceRecord,
]:
    invoices = {}

    with GROUND_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            invoice = (
                SyntheticInvoiceRecord.model_validate(
                    json.loads(line)
                )
            )

            invoices[invoice.invoice_number] = invoice

    return invoices


def save_ground_truth(
    invoices: list[SyntheticInvoiceRecord],
) -> None:
    BENCHMARK_GROUND_TRUTH_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with BENCHMARK_GROUND_TRUTH_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        for invoice in invoices:
            file.write(
                json.dumps(
                    invoice.model_dump(
                        mode="json"
                    )
                )
                + "\n"
            )


def create_corrupted_invoice(
    invoice: SyntheticInvoiceRecord,
    corruption_type: CorruptionType,
) -> SyntheticInvoiceRecord:
    if corruption_type == CorruptionType.TAX_MISMATCH:
        result = corrupt_tax(invoice)

    elif (
        corruption_type
        == CorruptionType.SUBTOTAL_MISMATCH
    ):
        result = corrupt_subtotal(invoice)

    elif (
        corruption_type
        == CorruptionType.TOTAL_MISMATCH
    ):
        result = corrupt_total(invoice)

    elif corruption_type == CorruptionType.MISSING_PO:
        result = remove_po(invoice)

    elif (
        corruption_type
        == CorruptionType.CURRENCY_MISMATCH
    ):
        result = corrupt_currency(invoice)

    else:
        raise ValueError(
            f"Unsupported benchmark corruption: "
            f"{corruption_type}"
        )

    return result.invoice


def main() -> None:
    invoices = load_invoices()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    renderer = InvoiceRenderer(
        output_directory=OUTPUT_DIRECTORY
    )

    benchmark_invoices = []
    manifest_documents = []

    # ---------------------------------------------------------------
    # Clean invoices
    #
    # One invoice for each of the seven PDF templates.
    # ---------------------------------------------------------------

    for index in range(1, 8):
        invoice_number = (
            f"INV-{index:05d}"
        )

        invoice = invoices[invoice_number]

        renderer.render(invoice)

        benchmark_invoices.append(invoice)

        manifest_documents.append(
            {
                "invoice_number": invoice_number,
                "category": "clean",
                "template": index,
            }
        )

    # ---------------------------------------------------------------
    # Controlled corruption cases.
    #
    # Each source invoice is different so we don't repeatedly
    # evaluate the exact same document.
    # ---------------------------------------------------------------

    corruption_plan = [
        (21, CorruptionType.TAX_MISMATCH),
        (22, CorruptionType.TAX_MISMATCH),
        (23, CorruptionType.TAX_MISMATCH),

        (24, CorruptionType.SUBTOTAL_MISMATCH),
        (25, CorruptionType.SUBTOTAL_MISMATCH),
        (26, CorruptionType.SUBTOTAL_MISMATCH),

        (27, CorruptionType.TOTAL_MISMATCH),
        (28, CorruptionType.TOTAL_MISMATCH),
        (29, CorruptionType.TOTAL_MISMATCH),

        (30, CorruptionType.MISSING_PO),
        (31, CorruptionType.MISSING_PO),
        (32, CorruptionType.MISSING_PO),

        (33, CorruptionType.CURRENCY_MISMATCH),
        (34, CorruptionType.CURRENCY_MISMATCH),
        (35, CorruptionType.CURRENCY_MISMATCH),
    ]

    for index, corruption_type in corruption_plan:
        invoice_number = (
            f"INV-{index:05d}"
        )

        source_invoice = invoices[
            invoice_number
        ]

        corrupted_invoice = (
            create_corrupted_invoice(
                source_invoice,
                corruption_type,
            )
        )

        renderer.render(
            corrupted_invoice
        )

        benchmark_invoices.append(
            corrupted_invoice
        )

        manifest_documents.append(
            {
                "invoice_number": invoice_number,
                "category": corruption_type.value,
                "template": (
                    (
                        index - 1
                    ) % 7
                ) + 1,
            }
        )

    save_ground_truth(
        benchmark_invoices
    )

    MANIFEST_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = {
        "version": 1,
        "description": (
            "Curated evaluation set for "
            "invoice extraction robustness."
        ),
        "documents": manifest_documents,
    }

    MANIFEST_PATH.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        f"Created {len(benchmark_invoices)} "
        "benchmark PDFs."
    )

    print(
        f"PDF directory: "
        f"{OUTPUT_DIRECTORY}"
    )

    print(
        f"Ground truth: "
        f"{BENCHMARK_GROUND_TRUTH_PATH}"
    )

    print(
        f"Evaluation manifest: "
        f"{MANIFEST_PATH}"
    )


if __name__ == "__main__":
    main()