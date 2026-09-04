from pathlib import Path

from app.evaluation.benchmark_results import BenchmarkResults
from app.evaluation.benchmark_state import BenchmarkState


def test_benchmark_results_persist_across_runs(
    tmp_path: Path,
) -> None:
    results_path = (
        tmp_path / "benchmark_results.jsonl"
    )

    manager = BenchmarkResults(
        results_path
    )

    first_result = {
        "invoice_number": "INV-00001",
        "category": "clean",
        "correct_fields": 9,
        "total_fields": 9,
        "accuracy": 1.0,
    }

    second_result = {
        "invoice_number": "INV-00002",
        "category": "tax_mismatch",
        "correct_fields": 8,
        "total_fields": 9,
        "accuracy": 8 / 9,
    }

    manager.append(first_result)
    manager.append(second_result)

    # Simulate a fresh process by creating
    # a new manager instance.
    new_manager = BenchmarkResults(
        results_path
    )

    results = new_manager.load()

    assert len(results) == 2
    assert results[0] == first_result
    assert results[1] == second_result


def test_benchmark_state_persists_progress(
    tmp_path: Path,
) -> None:
    state_path = (
        tmp_path / "benchmark_state.json"
    )

    manager = BenchmarkState(
        state_path
    )

    state = manager.load()

    state["completed"].append(
        "INV-00001"
    )

    state["completed"].append(
        "INV-00002"
    )

    manager.save(state)

    # Simulate a fresh process.
    new_manager = BenchmarkState(
        state_path
    )

    restored = new_manager.load()

    assert restored["completed"] == [
        "INV-00001",
        "INV-00002",
    ]


def test_benchmark_state_tracks_unavailable_models(
    tmp_path: Path,
) -> None:
    state_path = (
        tmp_path / "benchmark_state.json"
    )

    manager = BenchmarkState(
        state_path
    )

    state = manager.load()

    state["unavailable_models"].append(
        "gemini-3.6-flash"
    )

    manager.save(state)

    restored = manager.load()

    assert restored[
        "unavailable_models"
    ] == [
        "gemini-3.6-flash"
    ]