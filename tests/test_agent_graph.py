from decimal import Decimal
from pathlib import Path

from app.agent.graph import (
    build_graph,
    extraction_node,
    reflection_node,
    validation_node,
)
from app.agent.state import InvoiceAuditState
from app.schemas.extraction import ExtractedInvoice
from app.schemas.purchase_order import PurchaseOrder

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
            feedback: str | None = None,
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
            feedback: str | None = None,
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
            feedback: str | None = None,
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

def test_reflection_node_generates_feedback_for_failed_validation():
    from app.schemas.enums import ValidationStatus
    from app.schemas.validation import ValidationResult

    validation_result = ValidationResult(
        status=ValidationStatus.FAILED,
        calculated_subtotal=Decimal("2000.00"),
        calculated_tax=Decimal("360.00"),
        calculated_total=Decimal("2360.00"),
        subtotal_valid=True,
        tax_valid=False,
        total_valid=False,
        currency_valid=True,
        errors=[
            "Tax mismatch: expected 360.00, got 500.00.",
            "Total mismatch: expected 2360.00, got 2500.00.",
        ],
    )

    state: InvoiceAuditState = {
        "workflow_id": "wf-reflection-001",
        "validation_result": validation_result,
    }

    result = reflection_node(state)

    assert result["reflection_feedback"] is not None
    assert "Tax mismatch" in result["reflection_feedback"]
    assert "Total mismatch" in result["reflection_feedback"]
    assert "Do not mathematically correct" in result["reflection_feedback"]


def test_extraction_graph_retries_after_validation_failure(
    monkeypatch,
):
    valid_invoice = ExtractedInvoice(
        invoice_number="INV-RETRY-001",
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

    invalid_invoice = ExtractedInvoice(
        invoice_number="INV-RETRY-001",
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
        def __init__(self):
            self.calls = 0
            self.feedback_history = []

        def process(
            self,
            pdf_path: Path,
            feedback: str | None = None,
        ) -> ExtractedInvoice:
            self.calls += 1
            self.feedback_history.append(feedback)

            if self.calls == 1:
                return invalid_invoice

            return valid_invoice

    fake_pipeline = FakePipeline()

    monkeypatch.setattr(
        "app.agent.graph.InvoiceExtractionPipeline",
        lambda: fake_pipeline,
    )

    graph = build_graph()

    initial_state: InvoiceAuditState = {
        "workflow_id": "wf-retry-test-001",
        "document_path": "data/test/invoice.pdf",
        "extraction_attempts": 0,
    }

    result = graph.invoke(initial_state)

    assert result["extraction_attempts"] == 2
    assert result["validation_result"].status.value == "passed"
    assert result["invoice"].total == Decimal("2360.00")

    assert fake_pipeline.calls == 2
    assert fake_pipeline.feedback_history[0] is None
    assert fake_pipeline.feedback_history[1] is not None
    assert "Tax mismatch" in fake_pipeline.feedback_history[1]

def test_extraction_graph_stops_after_max_attempts(
    monkeypatch,
):
    invalid_invoice = ExtractedInvoice(
        invoice_number="INV-RETRY-FAIL-001",
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
        def __init__(self):
            self.calls = 0

        def process(
            self,
            pdf_path: Path,
            feedback: str | None = None,
        ) -> ExtractedInvoice:
            self.calls += 1
            return invalid_invoice

    fake_pipeline = FakePipeline()

    monkeypatch.setattr(
        "app.agent.graph.InvoiceExtractionPipeline",
        lambda: fake_pipeline,
    )

    graph = build_graph()

    initial_state: InvoiceAuditState = {
        "workflow_id": "wf-retry-limit-001",
        "document_path": "data/test/invoice.pdf",
        "extraction_attempts": 0,
    }

    result = graph.invoke(initial_state)

    assert result["extraction_attempts"] == 2
    assert result["validation_result"].status.value == "failed"
    assert fake_pipeline.calls == 2

def test_reconciliation_node_queries_erp_by_po():
    from app.agent.graph import create_reconciliation_node
    from app.schemas.invoice import Invoice

    invoice = Invoice(
        invoice_number="INV-RECON-001",
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

    purchase_order = PurchaseOrder(
        po_number="PO-8821",
        vendor="ABC Supplies",
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

    class FakeERPTools:
        def __init__(self):
            self.queried_po = None

        def query_erp_by_po(self, args):
            self.queried_po = args.po_number
            return purchase_order

        def search_erp_by_vendor(self, args):
            raise AssertionError(
                "Vendor search should not be used when PO exists."
            )

    fake_tools = FakeERPTools()

    node = create_reconciliation_node(
        fake_tools
    )

    result = node(
        {
            "workflow_id": "wf-recon-001",
            "invoice": invoice,
        }
    )

    assert fake_tools.queried_po == "PO-8821"
    assert (
        result["reconciliation_result"].status.value
        == "matched"
    )


def test_reconciliation_node_searches_erp_by_vendor_when_po_missing():
    from app.agent.graph import create_reconciliation_node
    from app.schemas.invoice import Invoice

    invoice = Invoice(
        invoice_number="INV-RECON-002",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number=None,
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

    purchase_order = PurchaseOrder(
        po_number="PO-8821",
        vendor="ABC Supplies",
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

    class FakeERPTools:
        def __init__(self):
            self.searched_vendor = None

        def query_erp_by_po(self, args):
            raise AssertionError(
                "PO query should not be used when PO is missing."
            )

        def search_erp_by_vendor(self, args):
            self.searched_vendor = args.vendor_name
            return [purchase_order]

    fake_tools = FakeERPTools()

    node = create_reconciliation_node(
        fake_tools
    )

    result = node(
        {
            "workflow_id": "wf-recon-002",
            "invoice": invoice,
        }
    )

    assert fake_tools.searched_vendor == "ABC Supplies"
    assert (
        result["reconciliation_result"].status.value
        == "matched"
    )