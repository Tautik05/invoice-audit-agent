from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agent.state import InvoiceAuditState
from app.extraction.normalizer import normalize_invoice
from app.extraction.pipeline import InvoiceExtractionPipeline
from app.schemas.enums import ValidationStatus
from app.validation.engine import validate_invoice


def extraction_node(state: InvoiceAuditState) -> dict:
    """Extract and normalize an invoice from the input PDF."""
    pipeline = InvoiceExtractionPipeline()
    extracted_invoice = pipeline.process(Path(state["document_path"]))
    invoice = normalize_invoice(extracted_invoice)

    return {
        "invoice": invoice,
        "extraction_attempts": (
            state.get("extraction_attempts", 0) + 1
        ),
    }


def validation_node(state: InvoiceAuditState) -> dict:
    """Run deterministic financial validation."""
    invoice = state["invoice"]
    validation_result = validate_invoice(invoice)

    return {
        "validation_result": validation_result,
    }


def route_after_validation(state: InvoiceAuditState) -> str:
    """Route the workflow based on validation status."""
    validation_result = state["validation_result"]

    if validation_result.status == ValidationStatus.PASSED:
        return "passed"

    return "failed"


def build_graph():
    """Build the invoice extraction and validation workflow."""
    graph = StateGraph(InvoiceAuditState)

    graph.add_node("extract", extraction_node)
    graph.add_node("validate", validation_node)

    graph.add_edge(START, "extract")
    graph.add_edge("extract", "validate")

    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "passed": END,
            "failed": END,
        },
    )

    return graph.compile()