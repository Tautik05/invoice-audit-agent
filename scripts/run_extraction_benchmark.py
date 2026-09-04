import json
import sys
import time
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.evaluation.benchmark_state import BenchmarkState
from app.evaluation.invoice_metrics import evaluate_invoice
from app.extraction.pipeline import InvoiceExtractionPipeline
from app.llm.errors import LLMError, LLMErrorType
from app.schemas.synthetic import SyntheticInvoiceRecord


GROUND_TRUTH_PATH = Path(
    "data/synthetic/ground_truth.jsonl"
)

PDF_DIRECTORY = Path(
    "data/synthetic/documents"
)

STATE_PATH = Path(
    "data/benchmark/benchmark_state.json"
)

NUMBER_OF_DOCUMENTS = 10


def load_ground_truth() -> dict[str, SyntheticInvoiceRecord]:
    records = {}

    with GROUND_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            invoice = SyntheticInvoiceRecord.model_validate(
                json.loads(line)
            )

            records[invoice.invoice_number] = invoice

    return records


def main() -> None:
    ground_truth = load_ground_truth()

    pipeline = InvoiceExtractionPipeline()

    evaluations = []

    state_manager = BenchmarkState(
        STATE_PATH
    )

    state = state_manager.load()

    print("=" * 80)
    print("INVOICE EXTRACTION BASELINE")
    print("=" * 80)

    print(
        f"Documents configured: {NUMBER_OF_DOCUMENTS}"
    )

    print(
        f"Previously completed: "
        f"{len(state['completed'])}"
    )

    if state["active_model"]:
        print(
            f"Previous active model: "
            f"{state['active_model']}"
        )

    print(
        f"Starting from invoice: "
        f"INV-{state['next_index']:05d}"
    )

    for index in range(
        state["next_index"],
        NUMBER_OF_DOCUMENTS + 1,
    ):
        invoice_number = f"INV-{index:05d}"

        if invoice_number in state["completed"]:
            print(
                f"\nSkipping {invoice_number}: "
                "already completed."
            )
            continue

        pdf_path = (
            PDF_DIRECTORY
            / f"{invoice_number}.pdf"
        )

        print(
            f"\nProcessing {invoice_number}..."
        )

        start_time = time.perf_counter()

        try:
            prediction = pipeline.process(
                pdf_path
            )

            elapsed = (
                time.perf_counter()
                - start_time
            )

            evaluation = evaluate_invoice(
                ground_truth[invoice_number],
                prediction,
            )

            evaluations.append(evaluation)

            state["completed"].append(
                invoice_number
            )

            state["next_index"] = index + 1

            state_manager.save(state)

            print(
                f"  Accuracy: "
                f"{evaluation.accuracy:.1%}"
            )

            print(
                f"  Time: {elapsed:.2f}s"
            )

            print(
                "  Progress saved."
            )

        except LLMError as exc:
            print(
                f"  ERROR: "
                f"{exc.error_type.value} - "
                f"{exc.message}"
            )

            if (
                exc.error_type
                == LLMErrorType.QUOTA_EXHAUSTED
            ):
                state["active_model"] = (
                    exc.model
                )

                state["next_index"] = index

                state_manager.save(state)

                print()
                print(
                    f"Quota exhausted for "
                    f"{exc.provider}/{exc.model}."
                )

                print(
                    "Benchmark progress saved."
                )

                print(
                    "Stopping benchmark safely."
                )

                break

            state["failed"].append(
                {
                    "invoice_number": invoice_number,
                    "error_type": (
                        exc.error_type.value
                    ),
                    "provider": exc.provider,
                    "model": exc.model,
                    "message": exc.message,
                }
            )

            state["next_index"] = index + 1

            state_manager.save(state)

        except Exception as exc:
            print(
                f"  ERROR: {exc}"
            )

            state["failed"].append(
                {
                    "invoice_number": invoice_number,
                    "error_type": "unknown",
                    "provider": None,
                    "model": None,
                    "message": str(exc),
                }
            )

            state["next_index"] = index + 1

            state_manager.save(state)

    if not evaluations:
        print(
            "\nNo new successful evaluations "
            "in this run."
        )

        print(
            f"Previously completed invoices: "
            f"{len(state['completed'])}"
        )

        print(
            f"Failed invoices recorded: "
            f"{len(state['failed'])}"
        )

        return

    field_accuracy = {
        "invoice_number": sum(
            e.invoice_number_correct
            for e in evaluations
        ),
        "vendor": sum(
            e.vendor_correct
            for e in evaluations
        ),
        "po_number": sum(
            e.po_number_correct
            for e in evaluations
        ),
        "currency": sum(
            e.currency_correct
            for e in evaluations
        ),
        "line_items": sum(
            e.line_items_correct
            for e in evaluations
        ),
        "subtotal": sum(
            e.subtotal_correct
            for e in evaluations
        ),
        "tax_rate": sum(
            e.tax_rate_correct
            for e in evaluations
        ),
        "tax": sum(
            e.tax_correct
            for e in evaluations
        ),
        "total": sum(
            e.total_correct
            for e in evaluations
        ),
    }

    print("\n")

    print("=" * 80)
    print("BASELINE RESULTS")
    print("=" * 80)

    print(
        f"Documents evaluated this run: "
        f"{len(evaluations)}"
    )

    print(
        f"Total completed documents: "
        f"{len(state['completed'])}"
    )

    print("\nField accuracy:")

    for field, correct in field_accuracy.items():
        accuracy = (
            correct
            / len(evaluations)
        )

        print(
            f"  {field:<20} "
            f"{accuracy:.1%}"
        )

    total_correct = sum(
        evaluation.correct_fields
        for evaluation in evaluations
    )

    total_fields = sum(
        evaluation.total_fields
        for evaluation in evaluations
    )

    print(
        f"\nOverall field accuracy: "
        f"{total_correct / total_fields:.1%}"
    )


if __name__ == "__main__":
    main()

