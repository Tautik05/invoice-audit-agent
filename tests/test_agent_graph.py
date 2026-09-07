from decimal import Decimal
from pathlib import Path

from app.agent.graph import (
    build_graph,
    extraction_node,
    validation_node,
)
from app.agent.state import InvoiceAuditState
from app.schemas.extraction import ExtractedInvoice


def test_extraction_node_normalizes_invoice(
    monkeypatch,
):
    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-TEST-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )

    class FakePipeline:
        def process(
            self,
            pdf_path: Path,
        ) -> ExtractedInvoice:
            assert pdf_path == Path(
                "data/test/invoice.pdf"
            )
            return extracted_invoice

    monkeypatch.setattr(
        "app.agent.graph.InvoiceExtractionPipeline",
        FakePipeline,
    )

    state: InvoiceAuditState = {
        "workflow_id": "wf-test-001",
        "document_path": "data/test/invoice.pdf",
        "extraction_attempts": 0,
    }

    result = extraction_node(state)

    assert result["invoice"].invoice_number == (
        "INV-TEST-001"
    )
    assert result["invoice"].vendor == (
        "ABC Supplies"
    )
    assert result["invoice"].po_number == (
        "PO-8821"
    )
    assert result["extraction_attempts"] == 1


def test_extraction_graph_runs_end_to_end(
    monkeypatch,
):
    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-GRAPH-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )

    class FakePipeline:
        def process(
            self,
            pdf_path: Path,
        ) -> ExtractedInvoice:
            return extracted_invoice

    monkeypatch.setattr(
        "app.agent.graph.InvoiceExtractionPipeline",
        FakePipeline,
    )

    graph = build_graph()

    initial_state: InvoiceAuditState = {
        "workflow_id": "wf-graph-test-001",
        "document_path": "data/test/invoice.pdf",
        "extraction_attempts": 0,
    }

    result = graph.invoke(initial_state)

    assert result["invoice"].invoice_number == (
        "INV-GRAPH-001"
    )
    assert result["invoice"].vendor == (
        "ABC Supplies"
    )
    assert result["extraction_attempts"] == 1

def test_validation_node_passes_valid_invoice():
    from app.schemas.invoice import Invoice

    invoice = Invoice(
        invoice_number="INV-VALID-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("360.00"),
        total=Decimal("2360.00"),
    )

    state: InvoiceAuditState = {
        "workflow_id": "wf-validation-001",
        "invoice": invoice,
    }

    result = validation_node(state)

    assert result["validation_result"].status.value == "passed"
    assert result["validation_result"].subtotal_valid is True
    assert result["validation_result"].tax_valid is True
    assert result["validation_result"].total_valid is True
    assert result["validation_result"].currency_valid is True


def test_validation_node_rejects_invalid_invoice():
    from app.schemas.invoice import Invoice

    invoice = Invoice(
        invoice_number="INV-INVALID-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("500.00"),
        total=Decimal("2500.00"),
    )

    state: InvoiceAuditState = {
        "workflow_id": "wf-validation-002",
        "invoice": invoice,
    }

    result = validation_node(state)

    assert result["validation_result"].status.value == "failed"
    assert result["validation_result"].subtotal_valid is True
    assert result["validation_result"].tax_valid is False
    assert result["validation_result"].total_valid is False
    assert result["validation_result"].errors


def test_extraction_graph_routes_invalid_invoice_to_failed_path(
    monkeypatch,
):
    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-GRAPH-INVALID-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("200.00"),
            }
        ],
        subtotal=Decimal("2000.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("500.00"),
        total=Decimal("2500.00"),
    )

    class FakePipeline:
        def process(
            self,
            pdf_path: Path,
        ) -> ExtractedInvoice:
            return extracted_invoice

    monkeypatch.setattr(
        "app.agent.graph.InvoiceExtractionPipeline",
        FakePipeline,
    )

    graph = build_graph()

    initial_state: InvoiceAuditState = {
        "workflow_id": "wf-graph-invalid-001",
        "document_path": "data/test/invoice.pdf",
        "extraction_attempts": 0,
    }

    result = graph.invoke(initial_state)

    assert result["invoice"].invoice_number == (
        "INV-GRAPH-INVALID-001"
    )
    assert result["validation_result"].status.value == "failed"
    assert result["validation_result"].tax_valid is False
    assert result["validation_result"].total_valid is False
