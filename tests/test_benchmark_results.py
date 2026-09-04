from pathlib import Path

from app.evaluation.benchmark_results import (
    BenchmarkResults,
)


def test_load_empty_results(
    tmp_path: Path,
):
    results = BenchmarkResults(
        tmp_path / "results.jsonl"
    )

    assert results.load() == []


def test_append_and_load_result(
    tmp_path: Path,
):
    results = BenchmarkResults(
        tmp_path / "results.jsonl"
    )

    result = {
        "invoice_number": "INV-00001",
        "category": "clean",
        "accuracy": 1.0,
    }

    results.append(result)

    assert results.load() == [result]


def test_results_are_persisted_as_jsonl(
    tmp_path: Path,
):
    path = tmp_path / "results.jsonl"

    results = BenchmarkResults(path)

    results.append(
        {
            "invoice_number": "INV-00001",
            "accuracy": 1.0,
        }
    )

    results.append(
        {
            "invoice_number": "INV-00002",
            "accuracy": 0.9,
        }
    )

    lines = path.read_text(
        encoding="utf-8"
    ).splitlines()

    assert len(lines) == 2