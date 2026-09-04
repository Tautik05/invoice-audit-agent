from app.evaluation.benchmark_metrics import (
    calculate_category_accuracy,
    calculate_field_accuracy,
    calculate_overall_accuracy,
)


def make_result(
    *,
    category: str,
    correct_fields: int,
    vendor_correct: bool = True,
) -> dict:
    return {
        "invoice_number": "INV-00001",
        "category": category,
        "invoice_number_correct": True,
        "vendor_correct": vendor_correct,
        "po_number_correct": True,
        "currency_correct": True,
        "line_items_correct": True,
        "subtotal_correct": True,
        "tax_rate_correct": True,
        "tax_correct": True,
        "total_correct": True,
        "correct_fields": correct_fields,
        "total_fields": 9,
        "accuracy": correct_fields / 9,
    }


def test_calculate_field_accuracy() -> None:
    results = [
        make_result(
            category="clean",
            correct_fields=9,
        ),
        make_result(
            category="clean",
            correct_fields=8,
            vendor_correct=False,
        ),
    ]

    accuracy = calculate_field_accuracy(
        results
    )

    assert accuracy["invoice_number"] == 1.0
    assert accuracy["vendor"] == 0.5
    assert accuracy["subtotal"] == 1.0
    assert accuracy["total"] == 1.0


def test_calculate_overall_accuracy() -> None:
    results = [
        make_result(
            category="clean",
            correct_fields=9,
        ),
        make_result(
            category="tax_mismatch",
            correct_fields=6,
        ),
    ]

    assert calculate_overall_accuracy(
        results
    ) == 15 / 18


def test_calculate_category_accuracy() -> None:
    results = [
        make_result(
            category="clean",
            correct_fields=9,
        ),
        make_result(
            category="clean",
            correct_fields=8,
        ),
        make_result(
            category="tax_mismatch",
            correct_fields=6,
        ),
    ]

    accuracy = calculate_category_accuracy(
        results
    )

    assert accuracy["clean"] == 17 / 18
    assert accuracy["tax_mismatch"] == 6 / 9


def test_empty_results() -> None:
    assert calculate_field_accuracy([]) == {}
    assert calculate_category_accuracy([]) == {}
    assert calculate_overall_accuracy([]) == 0.0