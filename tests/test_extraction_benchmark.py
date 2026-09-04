import json
from pathlib import Path

import pytest

from app.schemas.benchmark import (
    BenchmarkEvaluationSet,
)
from scripts.run_extraction_benchmark import (
    load_evaluation_set,
    validate_benchmark_inputs,
)


def test_load_evaluation_set():
    evaluation_set = load_evaluation_set()

    assert isinstance(
        evaluation_set,
        BenchmarkEvaluationSet,
    )

    assert len(
        evaluation_set.documents
    ) == 22


def test_evaluation_set_contains_expected_categories():
    evaluation_set = load_evaluation_set()

    categories = [
        document.category
        for document in evaluation_set.documents
    ]

    assert categories.count("clean") == 7
    assert categories.count("tax_mismatch") == 3
    assert categories.count("subtotal_mismatch") == 3
    assert categories.count("total_mismatch") == 3
    assert categories.count("missing_po") == 3
    assert categories.count("currency_mismatch") == 3


def test_validate_benchmark_inputs_rejects_missing_pdf(
    tmp_path: Path,
):
    manifest = {
        "version": 1,
        "description": "Test benchmark",
        "documents": [
            {
                "invoice_number": "INV-99999",
                "category": "clean",
                "template": 1,
            }
        ],
    }

    evaluation_set = (
        BenchmarkEvaluationSet.model_validate(
            manifest
        )
    )

    ground_truth = {}

    with pytest.raises(FileNotFoundError):
        validate_benchmark_inputs(
            evaluation_set,
            ground_truth,
        )