from collections import defaultdict
from typing import Any


FIELD_RESULT_KEYS = {
    "invoice_number": "invoice_number_correct",
    "vendor": "vendor_correct",
    "po_number": "po_number_correct",
    "currency": "currency_correct",
    "line_items": "line_items_correct",
    "subtotal": "subtotal_correct",
    "tax_rate": "tax_rate_correct",
    "tax": "tax_correct",
    "total": "total_correct",
}


def calculate_field_accuracy(
    results: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Calculate accuracy independently for every
    extracted field.
    """

    if not results:
        return {}

    accuracy = {}

    for field_name, result_key in FIELD_RESULT_KEYS.items():
        correct = sum(
            result[result_key]
            for result in results
        )

        accuracy[field_name] = (
            correct / len(results)
        )

    return accuracy


def calculate_overall_accuracy(
    results: list[dict[str, Any]],
) -> float:
    """
    Calculate overall field-level accuracy across
    all benchmark documents.
    """

    if not results:
        return 0.0

    total_correct = sum(
        result["correct_fields"]
        for result in results
    )

    total_fields = sum(
        result["total_fields"]
        for result in results
    )

    if total_fields == 0:
        return 0.0

    return total_correct / total_fields


def calculate_category_accuracy(
    results: list[dict[str, Any]],
) -> dict[str, float]:
    """
    Calculate overall field-level accuracy for
    each benchmark category.
    """

    if not results:
        return {}

    category_totals = defaultdict(
        lambda: {
            "correct": 0,
            "total": 0,
        }
    )

    for result in results:
        category = result["category"]

        category_totals[category]["correct"] += (
            result["correct_fields"]
        )

        category_totals[category]["total"] += (
            result["total_fields"]
        )

    return {
        category: (
            values["correct"]
            / values["total"]
        )
        for category, values
        in sorted(category_totals.items())
        if values["total"] > 0
    }