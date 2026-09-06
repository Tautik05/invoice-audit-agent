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


from app.evaluation.benchmark_metrics import (
    calculate_category_accuracy,
    calculate_field_accuracy,
    calculate_overall_accuracy,
)
from app.evaluation.benchmark_results import BenchmarkResults
from app.evaluation.benchmark_state import BenchmarkState
from app.evaluation.invoice_metrics import (
    InvoiceEvaluation,
    evaluate_invoice,
)
from app.evaluation.validation_metrics import (
    evaluate_validation,
)
from app.extraction.document import PDFTextExtractor
from app.extraction.extractor import InvoiceExtractor
from app.extraction.normalizer import normalize_invoice
from app.extraction.pipeline import InvoiceExtractionPipeline
from app.llm.errors import LLMError, LLMErrorType
from app.llm.router import LLMRouter
from app.llm.router_config import create_llm_router
from app.schemas.benchmark import BenchmarkEvaluationSet
from app.schemas.synthetic import SyntheticInvoiceRecord
from app.validation.engine import validate_invoice

BENCHMARK_GROUND_TRUTH_PATH = Path(
    "data/benchmark/ground_truth.jsonl"
)

PDF_DIRECTORY = Path(
    "data/benchmark/documents"
)

MANIFEST_PATH = Path(
    "data/benchmark/evaluation_set.json"
)

STATE_PATH = Path(
    "data/benchmark/benchmark_state.json"
)

RESULTS_PATH = Path(
    "data/benchmark/benchmark_results.jsonl"
)


def load_evaluation_set() -> BenchmarkEvaluationSet:
    data = json.loads(
        MANIFEST_PATH.read_text(
            encoding="utf-8"
        )
    )

    return BenchmarkEvaluationSet.model_validate(
        data
    )


def load_ground_truth() -> dict[
    str,
    SyntheticInvoiceRecord,
]:
    records = {}

    with BENCHMARK_GROUND_TRUTH_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        for line in file:
            invoice = (
                SyntheticInvoiceRecord.model_validate(
                    json.loads(line)
                )
            )

            records[invoice.invoice_number] = invoice

    return records


def validate_benchmark_inputs(
    evaluation_set: BenchmarkEvaluationSet,
    ground_truth: dict[
        str,
        SyntheticInvoiceRecord,
    ],
) -> None:
    """
    Validate every benchmark input before making
    any LLM API calls.
    """

    for document in evaluation_set.documents:
        invoice_number = document.invoice_number

        pdf_path = (
            PDF_DIRECTORY
            / f"{invoice_number}.pdf"
        )

        if not pdf_path.exists():
            raise FileNotFoundError(
                f"Benchmark PDF not found: "
                f"{pdf_path}"
            )

        if invoice_number not in ground_truth:
            raise ValueError(
                "Missing ground truth for "
                f"{invoice_number}."
            )


def create_benchmark_router(
    state: dict,
) -> LLMRouter:
    """
    Create an LLM router that excludes models
    known to be unavailable.
    """

    unavailable_models = set(
        state.get(
            "unavailable_models",
            [],
        )
    )

    base_router = create_llm_router()

    if not unavailable_models:
        return base_router

    available_models = [
        model
        for model in base_router.models
        if model.model not in unavailable_models
    ]

    if not available_models:
        raise RuntimeError(
            "No benchmark LLM models are available."
        )

    return LLMRouter(
        models=available_models,
        retry_policy=base_router.retry_policy,
        circuit_breaker=base_router.circuit_breaker,
    )


def evaluation_to_result(
    invoice_number: str,
    category: str,
    evaluation: InvoiceEvaluation,
    provider: str | None,
    model: str | None,
    latency_seconds: float,
) -> dict:
    """
    Convert an invoice evaluation into a
    persistable benchmark result.
    """

    return {
        "invoice_number": invoice_number,
        "category": category,
        "provider": provider,
        "model": model,
        "latency_seconds": round(
            latency_seconds,
            3,
        ),
        "invoice_number_correct": (
            evaluation.invoice_number_correct
        ),
        "vendor_correct": (
            evaluation.vendor_correct
        ),
        "po_number_correct": (
            evaluation.po_number_correct
        ),
        "currency_correct": (
            evaluation.currency_correct
        ),
        "line_items_correct": (
            evaluation.line_items_correct
        ),
        "subtotal_correct": (
            evaluation.subtotal_correct
        ),
        "tax_rate_correct": (
            evaluation.tax_rate_correct
        ),
        "tax_correct": (
            evaluation.tax_correct
        ),
        "total_correct": (
            evaluation.total_correct
        ),
        "correct_fields": evaluation.correct_fields,
        "total_fields": evaluation.total_fields,
        "accuracy": evaluation.accuracy,
    }


def result_to_evaluation(
    result: dict,
) -> InvoiceEvaluation:
    """
    Reconstruct InvoiceEvaluation from a persisted
    benchmark result.
    """

    return InvoiceEvaluation(
        invoice_number_correct=result[
            "invoice_number_correct"
        ],
        vendor_correct=result[
            "vendor_correct"
        ],
        po_number_correct=result[
            "po_number_correct"
        ],
        currency_correct=result[
            "currency_correct"
        ],
        line_items_correct=result[
            "line_items_correct"
        ],
        subtotal_correct=result[
            "subtotal_correct"
        ],
        tax_rate_correct=result[
            "tax_rate_correct"
        ],
        tax_correct=result[
            "tax_correct"
        ],
        total_correct=result[
            "total_correct"
        ],
    )

def print_benchmark_configuration(
    evaluation_set: BenchmarkEvaluationSet,
    router: LLMRouter,
    state: dict,
    existing_results: list[dict],
) -> None:
    print("=" * 80)
    print("INVOICE EXTRACTION BASELINE")
    print("=" * 80)

    print(
        f"Documents configured: "
        f"{len(evaluation_set.documents)}"
    )

    print(
        f"Previously completed: "
        f"{len(state['completed'])}"
    )

    print(
        f"Persisted evaluation results: "
        f"{len(existing_results)}"
    )

    unavailable_models = state.get(
        "unavailable_models",
        [],
    )

    if unavailable_models:
        print(
            "Previously unavailable models:"
        )

        for model in sorted(
            unavailable_models
        ):
            print(f"  - {model}")

    print("\nActive benchmark models:")

    for model in router.models:
        print(
            f"  - {model.provider}/"
            f"{model.model}"
        )


def calculate_results(
    results: list[dict],
) -> None:
    if not results:
        print(
            "\nNo successful benchmark "
            "results available."
        )
        return

    field_accuracy = calculate_field_accuracy(
        results
    )

    overall_accuracy = (
        calculate_overall_accuracy(results)
    )

    category_accuracy = (
        calculate_category_accuracy(results)
    )

    valid_latencies = [
        result["latency_seconds"]
        for result in results
        if result.get("latency_seconds")
        is not None
    ]

    average_latency = (
        sum(valid_latencies)
        / len(valid_latencies)
        if valid_latencies
        else None
    )

    model_usage: dict[str, int] = {}

    for result in results:
        provider = result.get("provider")
        model = result.get("model")

        if provider and model:
            model_key = (
                f"{provider}/{model}"
            )

            model_usage[model_key] = (
                model_usage.get(model_key, 0)
                + 1
            )

    print("\n")
    print("=" * 80)
    print("BENCHMARK RESULTS")
    print("=" * 80)

    print(
        f"Documents evaluated: "
        f"{len(results)}"
    )

    if average_latency is not None:
        print(
            f"Average extraction latency: "
            f"{average_latency:.2f}s"
        )

    print("\nField accuracy:")

    for field, accuracy in field_accuracy.items():
        print(
            f"  {field:<20} "
            f"{accuracy:.1%}"
        )

    print(
        f"\nOverall field accuracy: "
        f"{overall_accuracy:.1%}"
    )

    print("\nCategory accuracy:")

    for category, accuracy in (
        category_accuracy.items()
    ):
        category_count = sum(
            result["category"] == category
            for result in results
        )

        print(
            f"  {category:<20} "
            f"{accuracy:.1%} "
            f"({category_count} docs)"
        )

    print("\nModel usage:")

    if model_usage:
        for model, count in sorted(
            model_usage.items()
        ):
            print(
                f"  {model:<40} "
                f"{count} docs"
            )
    else:
        print("  No model metadata available.")


def main() -> None:
    evaluation_set = (
        load_evaluation_set()
    )

    ground_truth = load_ground_truth()

    # Validate the complete benchmark before
    # constructing or calling any LLM provider.
    validate_benchmark_inputs(
        evaluation_set,
        ground_truth,
    )

    state_manager = BenchmarkState(
        STATE_PATH
    )

    state = state_manager.load()

    results_manager = BenchmarkResults(
        RESULTS_PATH
    )

    existing_results = (
        results_manager.load()
    )

    existing_result_ids = {
        result["invoice_number"]
        for result in existing_results
    }

    router = create_benchmark_router(
        state
    )

    invoice_extractor = InvoiceExtractor(
        llm_router=router
    )

    pipeline = InvoiceExtractionPipeline(
        document_extractor=PDFTextExtractor(),
        invoice_extractor=invoice_extractor,
    )

    print_benchmark_configuration(
        evaluation_set,
        router,
        state,
        existing_results,
    )

    for document in evaluation_set.documents:
        invoice_number = (
            document.invoice_number
        )

        if (
            invoice_number in state["completed"]
            or invoice_number in existing_result_ids
        ):
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
            f"\nProcessing {invoice_number} "
            f"[{document.category}]..."
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
                ground_truth[
                    invoice_number
                ],
                prediction,
            )

            if (
                router.last_used_provider is None
                or router.last_used_model is None
            ):
                raise RuntimeError(
                    "LLM router returned a response "
                    "without recording the "
                    "provider/model used."
                )

            result = evaluation_to_result(
                invoice_number=invoice_number,
                category=document.category,
                evaluation=evaluation,
                provider=router.last_used_provider,
                model=router.last_used_model,
                latency_seconds=elapsed,
            )

            # Persist the evaluation immediately so
            # progress survives interruption.
            results_manager.append(result)
            existing_results.append(result)

            existing_result_ids.add(
                invoice_number
            )

            if invoice_number not in state[
                "completed"
            ]:
                state["completed"].append(
                    invoice_number
                )

            state_manager.save(state)

            print(
                f"  Accuracy: "
                f"{evaluation.accuracy:.1%}"
            )

            print(
                f"  Time: {elapsed:.2f}s"
            )

            print(
                f"  Model: "
                f"{router.last_used_provider}/"
                f"{router.last_used_model}"
            )

            print(
                "  Result persisted."
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
                if exc.model not in state[
                    "unavailable_models"
                ]:
                    state[
                        "unavailable_models"
                    ].append(exc.model)

                state_manager.save(state)

                print()
                print(
                    f"Quota exhausted for "
                    f"{exc.provider}/"
                    f"{exc.model}."
                )

                print(
                    "Benchmark progress saved."
                )

                print(
                    "The model will be excluded "
                    "on the next run."
                )

                print(
                    "Stopping benchmark safely."
                )

                break

            state["failed"].append(
                {
                    "invoice_number":
                        invoice_number,
                    "error_type":
                        exc.error_type.value,
                    "provider":
                        exc.provider,
                    "model":
                        exc.model,
                    "message":
                        exc.message,
                }
            )

            state_manager.save(state)

        except Exception as exc:
            print(
                f"  ERROR: {exc}"
            )

            state["failed"].append(
                {
                    "invoice_number":
                        invoice_number,
                    "error_type":
                        "unknown",
                    "provider":
                        None,
                    "model":
                        None,
                    "message":
                        str(exc),
                }
            )

            state_manager.save(state)

    # Always calculate from ALL persisted results,
    # not only results generated during this run.
    final_results = (
        results_manager.load()
    )

    calculate_results(
        final_results
    )

    print()

    print(
        f"Completed documents: "
        f"{len(state['completed'])}"
    )

    print(
        f"Failed documents: "
        f"{len(state['failed'])}"
    )


if __name__ == "__main__":
    main()