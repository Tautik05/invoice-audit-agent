from decimal import Decimal
from pathlib import Path

from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from app.agent.graph import build_audit_graph
from app.agent.tools.erp_tools import ERPTools
from app.main import app
from app.schemas.extraction import ExtractedInvoice
from app.erp.repository import ERPRepository

def test_health_check() -> None:
    """Health endpoint returns a successful response."""
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_submit_invoice_rejects_non_pdf() -> None:
    """Invoice endpoint rejects non-PDF uploads."""
    with TestClient(app) as client:
        response = client.post(
            "/invoices",
            files={
                "file": (
                    "invoice.txt",
                    b"not a pdf",
                    "text/plain",
                )
            },
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF files are accepted."


def test_submit_invoice_auto_settles_matched_invoice(
    erp_service,
    session_factory,
) -> None:
    """Matched invoices are processed and settled through the API."""

    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-API-001",
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
            assert pdf_path.exists()
            return extracted_invoice

    graph = build_audit_graph(
        ERPTools(erp_service),
        extraction_pipeline=FakePipeline(),
        checkpointer=MemorySaver(),
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        app.state.audit_graph = graph

        response = client.post(
            "/invoices",
            files={
                "file": (
                    "invoice.pdf",
                    b"%PDF-fake-invoice",
                    "application/pdf",
                )
            },
        )

    assert response.status_code == 200

    body = response.json()

    assert body["workflow_id"]
    assert body["status"] == "completed"
    assert body["message"] == "Invoice processing completed."


def test_submit_invoice_then_approve_human_review(
    erp_service,
    session_factory,
) -> None:
    """Invoices with reconciliation variance can be approved through the API."""

    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-HITL-APPROVE-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("210.00"),
            }
        ],
        subtotal=Decimal("2100.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("378.00"),
        total=Decimal("2478.00"),
    )

    class FakePipeline:
        def process(
            self,
            pdf_path: Path,
            feedback: str | None = None,
        ) -> ExtractedInvoice:
            assert pdf_path.exists()
            return extracted_invoice

    graph = build_audit_graph(
        ERPTools(erp_service),
        extraction_pipeline=FakePipeline(),
        checkpointer=MemorySaver(),
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        app.state.audit_graph = graph
        app.state.session_factory = session_factory

        response = client.post(
            "/invoices",
            files={
                "file": (
                    "invoice.pdf",
                    b"%PDF-fake-invoice",
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 200

        submission = response.json()

        workflow_id = submission["workflow_id"]

        assert submission["status"] == "waiting_for_human"
        assert submission["message"] == (
            "Invoice requires human review."
        )

        workflow_response = client.get(
            f"/workflows/{workflow_id}"
        )

        assert workflow_response.status_code == 200
        assert workflow_response.json()["status"] == (
            "waiting_for_human"
        )

        approval_response = client.post(
            f"/workflows/{workflow_id}/approve"
        )

        assert approval_response.status_code == 200

        approval_body = approval_response.json()

        assert approval_body["workflow_id"] == workflow_id
        assert approval_body["status"] == "completed"
        assert approval_body["message"] == (
            "Workflow approved successfully."
        )

        final_workflow_response = client.get(
            f"/workflows/{workflow_id}"
        )

        assert final_workflow_response.status_code == 200
        assert final_workflow_response.json()["status"] == (
            "completed"
        )


def test_submit_invoice_then_reject_human_review(
    erp_service,
    session_factory,
) -> None:
    """Invoices requiring review can be rejected through the API."""

    extracted_invoice = ExtractedInvoice(
        invoice_number="INV-HITL-REJECT-001",
        vendor="ABC Supplies",
        invoice_date=None,
        po_number="PO-8821",
        currency="USD",
        line_items=[
            {
                "description": "Monitor",
                "quantity": 10,
                "unit_price": Decimal("210.00"),
            }
        ],
        subtotal=Decimal("2100.00"),
        tax_rate=Decimal("0.18"),
        tax=Decimal("378.00"),
        total=Decimal("2478.00"),
    )

    class FakePipeline:
        def process(
            self,
            pdf_path: Path,
            feedback: str | None = None,
        ) -> ExtractedInvoice:
            assert pdf_path.exists()
            return extracted_invoice

    graph = build_audit_graph(
        ERPTools(erp_service),
        extraction_pipeline=FakePipeline(),
        checkpointer=MemorySaver(),
        session_factory=session_factory,
    )

    with TestClient(app) as client:
        app.state.audit_graph = graph
        app.state.session_factory = session_factory

        response = client.post(
            "/invoices",
            files={
                "file": (
                    "invoice.pdf",
                    b"%PDF-fake-invoice",
                    "application/pdf",
                )
            },
        )

        assert response.status_code == 200

        submission = response.json()

        workflow_id = submission["workflow_id"]

        assert submission["status"] == "waiting_for_human"

        rejection_response = client.post(
            f"/workflows/{workflow_id}/reject"
        )

        assert rejection_response.status_code == 200

        rejection_body = rejection_response.json()

        assert rejection_body["workflow_id"] == workflow_id
        assert rejection_body["status"] == "rejected"
        assert rejection_body["message"] == (
            "Workflow rejected successfully."
        )

        workflow_response = client.get(
            f"/workflows/{workflow_id}"
        )

        assert workflow_response.status_code == 200
        assert workflow_response.json()["status"] == "rejected"

        audit_response = client.get(
            f"/workflows/{workflow_id}/audit"
        )

        assert audit_response.status_code == 200

        events = audit_response.json()["events"]

        event_types = [
            event["event_type"]
            for event in events
        ]

        assert "human_review_requested" in event_types
        assert "human_rejected" in event_types
        assert "invoice_settled" not in event_types


def test_get_workflow_returns_current_status() -> None:
    """Workflow endpoint returns the persisted workflow status."""

    from langgraph.graph import END, START, StateGraph

    from app.agent.state import InvoiceAuditState
    from app.schemas.enums import WorkflowStatus

    def set_status(state: InvoiceAuditState):
        return {
            "workflow_status": WorkflowStatus.WAITING_FOR_HUMAN,
        }

    builder = StateGraph(InvoiceAuditState)

    builder.add_node("set_status", set_status)
    builder.add_edge(START, "set_status")
    builder.add_edge("set_status", END)

    graph = builder.compile(
        checkpointer=MemorySaver(),
    )

    workflow_id = "wf-api-status-001"

    graph.invoke(
        {
            "workflow_id": workflow_id,
        },
        config={
            "configurable": {
                "thread_id": workflow_id,
            }
        },
    )

    app.state.audit_graph = graph

    with TestClient(app) as client:
        response = client.get(
            f"/workflows/{workflow_id}"
        )

    assert response.status_code == 200

    body = response.json()

    assert body["workflow_id"] == workflow_id
    assert body["status"] == "waiting_for_human"
    assert body["message"] == "Invoice requires human review."


def test_get_workflow_returns_404_for_unknown_workflow() -> None:
    """Unknown workflow IDs return 404."""

    from langgraph.graph import END, START, StateGraph

    from app.agent.state import InvoiceAuditState

    builder = StateGraph(InvoiceAuditState)

    builder.add_node(
        "noop",
        lambda state: {},
    )
    builder.add_edge(START, "noop")
    builder.add_edge("noop", END)

    graph = builder.compile(
        checkpointer=MemorySaver(),
    )

    app.state.audit_graph = graph

    with TestClient(app) as client:
        response = client.get(
            "/workflows/nonexistent-workflow"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Workflow not found."


def test_get_workflow_audit_returns_events(
    session_factory,
) -> None:
    """Audit endpoint returns persisted workflow events."""

    workflow_id = "wf-api-audit-001"

    with session_factory() as session:
        repository = ERPRepository(session)

        repository.add_audit_event(
            workflow_id=workflow_id,
            event_type="extraction_completed",
            actor="agent",
            details={
                "attempt": 1,
                "invoice_number": "INV-API-001",
            },
            idempotency_key=f"test:extraction:{workflow_id}",
        )

        repository.add_audit_event(
            workflow_id=workflow_id,
            event_type="validation_completed",
            actor="agent",
            details={
                "status": "passed",
            },
            idempotency_key=f"test:validation:{workflow_id}",
        )

        session.commit()

    app.state.session_factory = session_factory

    with TestClient(app) as client:
        response = client.get(
            f"/workflows/{workflow_id}/audit"
        )

    assert response.status_code == 200

    body = response.json()

    assert body["workflow_id"] == workflow_id
    assert len(body["events"]) == 2

    assert body["events"][0]["event_type"] == (
        "extraction_completed"
    )
    assert body["events"][0]["actor"] == "agent"
    assert body["events"][0]["details"] == {
        "attempt": 1,
        "invoice_number": "INV-API-001",
    }

    assert body["events"][1]["event_type"] == (
        "validation_completed"
    )
    assert body["events"][1]["details"] == {
        "status": "passed",
    }


def test_get_workflow_audit_returns_empty_events(
    session_factory,
) -> None:
    """Workflow with no audit events returns an empty list."""

    workflow_id = "wf-api-audit-empty-001"

    app.state.session_factory = session_factory

    with TestClient(app) as client:
        response = client.get(
            f"/workflows/{workflow_id}/audit"
        )

    assert response.status_code == 200

    body = response.json()

    assert body["workflow_id"] == workflow_id
    assert body["events"] == []