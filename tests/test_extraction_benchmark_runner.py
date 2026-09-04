from app.evaluation.invoice_metrics import InvoiceEvaluation

from scripts.run_extraction_benchmark import (
    evaluation_to_result,
    result_to_evaluation,
)


def make_evaluation() -> InvoiceEvaluation:
    return InvoiceEvaluation(
        invoice_number_correct=True,
        vendor_correct=True,
        po_number_correct=False,
        currency_correct=True,
        line_items_correct=True,
        subtotal_correct=True,
        tax_rate_correct=False,
        tax_correct=True,
        total_correct=False,
    )


def test_evaluation_to_result() -> None:
    evaluation = make_evaluation()

    result = evaluation_to_result(
        invoice_number="INV-00021",
        category="tax_mismatch",
        evaluation=evaluation,
        provider="gemini",
        model="gemini-3.6-flash",
        latency_seconds=12.34,
    )

    assert result["invoice_number"] == "INV-00021"
    assert result["category"] == "tax_mismatch"

    assert result["provider"] == "gemini"
    assert result["model"] == "gemini-3.6-flash"
    assert result["latency_seconds"] == 12.34

    assert result["invoice_number_correct"] is True
    assert result["vendor_correct"] is True
    assert result["po_number_correct"] is False
    assert result["currency_correct"] is True
    assert result["line_items_correct"] is True
    assert result["subtotal_correct"] is True
    assert result["tax_rate_correct"] is False
    assert result["tax_correct"] is True
    assert result["total_correct"] is False

    assert result["correct_fields"] == 6
    assert result["total_fields"] == 9
    assert result["accuracy"] == 6 / 9


def test_result_to_evaluation() -> None:
    original = make_evaluation()

    result = evaluation_to_result(
        invoice_number="INV-00021",
        category="tax_mismatch",
        evaluation=original,
        provider="gemini",
        model="gemini-3.6-flash",
        latency_seconds=12.34,
    )

    restored = result_to_evaluation(result)

    assert restored == original


def test_result_round_trip_preserves_accuracy() -> None:
    evaluation = make_evaluation()

    result = evaluation_to_result(
        invoice_number="INV-00021",
        category="tax_mismatch",
        evaluation=evaluation,
        provider="gemini",
        model="gemini-3.6-flash",
        latency_seconds=12.34,
    )

    restored = result_to_evaluation(result)

    assert (
        restored.correct_fields
        == evaluation.correct_fields
    )

    assert (
        restored.total_fields
        == evaluation.total_fields
    )

    assert (
        restored.accuracy
        == evaluation.accuracy
    )