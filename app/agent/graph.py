from pathlib import Path

from langgraph.graph import END, START, StateGraph

from app.agent.state import InvoiceAuditState
from app.extraction.normalizer import normalize_invoice
from app.extraction.pipeline import InvoiceExtractionPipeline
from app.schemas.enums import ValidationStatus
from app.validation.engine import validate_invoice
from app.agent.tools.erp_tools import ERPTools
from app.reconciliation.engine import reconcile_invoice
from app.schemas.tools import (
    QueryPurchaseOrderArgs,
    SearchPurchaseOrdersArgs,
)

MAX_EXTRACTION_ATTEMPTS = 2


def extraction_node(state: InvoiceAuditState) -> dict:
    """Extract and normalize an invoice from the input PDF."""
    pipeline = InvoiceExtractionPipeline()

    extracted_invoice = pipeline.process(
        Path(state["document_path"]),
        feedback=state.get("reflection_feedback"),
    )

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


def reflection_node(state: InvoiceAuditState) -> dict:
    """Generate feedback for a failed extraction attempt."""
    validation_result = state["validation_result"]

    errors = validation_result.errors

    if not errors:
        return {
            "reflection_feedback": None,
        }

    feedback = (
        "The previous extraction failed deterministic validation. "
        "Re-examine the source document and extract the values "
        "exactly as printed. Do not mathematically correct the "
        "invoice.\n\n"
        "Validation issues:\n"
        + "\n".join(f"- {error}" for error in errors)
    )

    return {
        "reflection_feedback": feedback,
    }


def route_after_validation(state: InvoiceAuditState) -> str:
    """Route the workflow based on validation status."""
    validation_result = state["validation_result"]

    if validation_result.status == ValidationStatus.PASSED:
        return "passed"

    return "failed"


def route_after_reflection(state: InvoiceAuditState) -> str:
    """Decide whether another extraction attempt is allowed."""
    if (
        state.get("extraction_attempts", 0)
        < MAX_EXTRACTION_ATTEMPTS
    ):
        return "retry"

    return "stop"


def create_reconciliation_node(
    erp_tools: ERPTools,
):
    """Create a reconciliation node bound to ERP tools."""

    def reconciliation_node(
        state: InvoiceAuditState,
    ) -> dict:
        """Reconcile the invoice against ERP purchase-order data."""
        invoice = state["invoice"]

        if invoice.po_number:
            purchase_order = erp_tools.query_erp_by_po(
                QueryPurchaseOrderArgs(
                    po_number=invoice.po_number
                )
            )
        else:
            purchase_orders = erp_tools.search_erp_by_vendor(
                SearchPurchaseOrdersArgs(
                    vendor_name=invoice.vendor
                )
            )

            if len(purchase_orders) == 1:
                purchase_order = purchase_orders[0]
            else:
                purchase_order = None

        result = reconcile_invoice(
            invoice,
            purchase_order,
        )

        return {
            "reconciliation_result": result,
        }

    return reconciliation_node

def build_graph():
    """Build the invoice extraction and validation workflow."""
    graph = StateGraph(InvoiceAuditState)

    graph.add_node("extract", extraction_node)
    graph.add_node("validate", validation_node)
    graph.add_node("reflect", reflection_node)

    graph.add_edge(START, "extract")
    graph.add_edge("extract", "validate")

    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "passed": END,
            "failed": "reflect",
        },
    )

    graph.add_conditional_edges(
        "reflect",
        route_after_reflection,
        {
            "retry": "extract",
            "stop": END,
        },
    )

    return graph.compile()