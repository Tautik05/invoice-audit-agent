import pytest
from pydantic import ValidationError

from app.schemas.benchmark import (
    BenchmarkDocument,
    BenchmarkEvaluationSet,
)


def test_benchmark_document_valid():
    document = BenchmarkDocument(
        invoice_number="INV-00001",
        category="clean",
        template=1,
    )

    assert document.invoice_number == "INV-00001"
    assert document.category == "clean"
    assert document.template == 1


def test_benchmark_document_allows_missing_template():
    document = BenchmarkDocument(
        invoice_number="INV-00008",
        category="tax_mismatch",
    )

    assert document.template is None


def test_benchmark_document_rejects_invalid_template():
    with pytest.raises(ValidationError):
        BenchmarkDocument(
            invoice_number="INV-00001",
            category="clean",
            template=0,
        )


def test_benchmark_evaluation_set_valid():
    evaluation_set = BenchmarkEvaluationSet(
        version=1,
        description="Test benchmark",
        documents=[
            BenchmarkDocument(
                invoice_number="INV-00001",
                category="clean",
                template=1,
            )
        ],
    )

    assert evaluation_set.version == 1
    assert len(evaluation_set.documents) == 1


def test_benchmark_evaluation_set_requires_documents():
    with pytest.raises(ValidationError):
        BenchmarkEvaluationSet(
            version=1,
            description="Test benchmark",
            documents=[],
        )