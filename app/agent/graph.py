from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from app.agent.state import InvoiceAuditState
from app.agent.tools.erp_tools import ERPTools
from app.db.session import SessionLocal
from app.decision.engine import decide_invoice_action
from app.erp.unit_of_work import ERPUnitOfWork
from app.extraction.normalizer import normalize_invoice
from app.extraction.pipeline import InvoiceExtractionPipeline
from app.reconciliation.engine import (
    build_ambiguous_result,
    reconcile_invoice,
)
from app.schemas.enums import (
    AuditEventType,
    DecisionAction,
    HumanDecision,
    ReconciliationStatus,
    ValidationStatus,
    WorkflowStatus,
)
from app.schemas.tools import (
    CheckDuplicateInvoiceArgs,
    QueryPurchaseOrderArgs,
    SearchPurchaseOrdersArgs,
)
from app.validation.engine import validate_invoice


MAX_EXTRACTION_ATTEMPTS = 2


def _enum_value(value):
    """Return an enum value as a plain string."""
    return value.value if hasattr(value, "value") else value

def record_workflow_audit_event(
    session_factory,
    workflow_id: str,
    event_type: AuditEventType,
    details: dict | None = None,
    actor: str = "agent",
    idempotency_key: str | None = None,
) -> None:
    """Persist a workflow audit event independently of graph state."""

    with ERPUnitOfWork(session_factory) as uow:
        if uow.repository is None:
            raise RuntimeError(
                "ERP repository is not initialized."
            )

        uow.repository.add_audit_event(
            workflow_id=workflow_id,
            event_type=event_type.value,
            actor=actor,
            details=details,
            idempotency_key=idempotency_key,
        )

        uow.commit()


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


def create_extraction_node(
    pipeline: InvoiceExtractionPipeline,
    session_factory=SessionLocal,
):
    """Create an extraction node bound to an extraction pipeline."""

    def injected_extraction_node(
        state: InvoiceAuditState,
    ) -> dict:
        """Extract and normalize using the supplied pipeline."""

        extracted_invoice = pipeline.process(
            Path(state["document_path"]),
            feedback=state.get("reflection_feedback"),
        )

        invoice = normalize_invoice(extracted_invoice)

        attempt = (
            state.get("extraction_attempts", 0) + 1
        )

        record_workflow_audit_event(
            session_factory=session_factory,
            workflow_id=state["workflow_id"],
            event_type=AuditEventType.EXTRACTION_COMPLETED,
            idempotency_key=(
                f"extraction_completed:"
                f"{state['workflow_id']}:"
                f"{attempt}"
            ),
            details={
                "attempt": attempt,
                "invoice_number": invoice.invoice_number,
                "vendor": invoice.vendor,
            },
        )

        return {
            "invoice": invoice,
            "extraction_attempts": attempt,
        }

    return injected_extraction_node


def validation_node(
    state: InvoiceAuditState,
    session_factory=SessionLocal,
) -> dict:
    """Run deterministic financial validation."""

    invoice = state["invoice"]

    validation_result = validate_invoice(invoice)

    attempt = state.get("extraction_attempts", 1)

    record_workflow_audit_event(
        session_factory=session_factory,
        workflow_id=state["workflow_id"],
        event_type=AuditEventType.VALIDATION_COMPLETED,
        idempotency_key=(
            f"validation_completed:"
            f"{state['workflow_id']}:"
            f"{attempt}"
        ),
        details={
            "attempt": attempt,
            "status": validation_result.status.value,
            "errors": validation_result.errors,
        },
    )

    return {
        "validation_result": validation_result
    }

def create_duplicate_check_node(
    erp_tools: ERPTools,
    session_factory=SessionLocal,
):
    """Create a duplicate-invoice check node bound to ERP tools."""

    def duplicate_check_node(
        state: InvoiceAuditState,
    ) -> dict:
        """Check whether the invoice has already been settled."""

        invoice = state["invoice"]

        duplicate_invoice = (
            erp_tools.check_duplicate_invoice(
                CheckDuplicateInvoiceArgs(
                    invoice_number=invoice.invoice_number
                )
            )
        )

        record_workflow_audit_event(
            session_factory=session_factory,
            workflow_id=state["workflow_id"],
            event_type=AuditEventType.DUPLICATE_CHECK_COMPLETED,
            idempotency_key=(
                f"duplicate_check_completed:"
                f"{state['workflow_id']}"
            ),
            details={
                "invoice_number": invoice.invoice_number,
                "duplicate": duplicate_invoice,
            },
        )

        return {
            "duplicate_invoice": duplicate_invoice,
        }

    return duplicate_check_node

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


def validation_failure_node(
    state: InvoiceAuditState,
) -> dict:
    """Mark the workflow as failed after exhausting extraction attempts."""

    return {
        "workflow_status": WorkflowStatus.FAILED,
        "error": (
            "Invoice failed deterministic validation "
            "after the maximum extraction attempts."
        ),
    }


def create_reconciliation_node(
    erp_tools: ERPTools,
    session_factory=SessionLocal,
):
    """Create a reconciliation node bound to ERP tools."""

    def reconciliation_node(
        state: InvoiceAuditState,
    ) -> dict:
        invoice = state["invoice"]

        if invoice.po_number:
            purchase_order = erp_tools.query_erp_by_po(
                QueryPurchaseOrderArgs(
                    po_number=invoice.po_number
                )
            )

            if purchase_order is None:
                result = reconcile_invoice(
                    invoice,
                    None,
                )
            else:
                result = reconcile_invoice(
                    invoice,
                    purchase_order,
                )

        else:
            purchase_orders = erp_tools.search_erp_by_vendor(
                SearchPurchaseOrdersArgs(
                    vendor_name=invoice.vendor
                )
            )

            if len(purchase_orders) == 0:
                result = reconcile_invoice(
                    invoice,
                    None,
                )

            elif len(purchase_orders) == 1:
                result = reconcile_invoice(
                    invoice,
                    purchase_orders[0],
                )

            else:
                result = build_ambiguous_result(
                    invoice,
                    candidate_count=len(purchase_orders),
                )

        record_workflow_audit_event(
            session_factory=session_factory,
            workflow_id=state["workflow_id"],
            event_type=AuditEventType.RECONCILIATION_COMPLETED,
            idempotency_key=(
                f"reconciliation_completed:"
                f"{state['workflow_id']}"
            ),
            details={
                "status": result.status.value,
                "result": result.model_dump(
                    mode="json"
                ),
            },
        )

        return {
            "reconciliation_result": result
        }

    return reconciliation_node


def decision_node(
    state: InvoiceAuditState,
    session_factory=SessionLocal,
) -> dict:
    """Determine the next action from reconciliation results."""

    reconciliation_result = state[
        "reconciliation_result"
    ]

    decision_result = decide_invoice_action(
        reconciliation_result,
        duplicate_invoice=state.get(
            "duplicate_invoice",
            False,
        ),
    )

    workflow_id = state.get("workflow_id")

    if workflow_id is not None:
        record_workflow_audit_event(
            session_factory=session_factory,
            workflow_id=workflow_id,
            event_type=AuditEventType.DECISION_MADE,
            idempotency_key=(
                f"decision_made:"
                f"{workflow_id}"
            ),
            details={
                "action": decision_result.action.value,
                "reasons": decision_result.reasons,
            },
        )

    return {
        "decision_result": decision_result,
        "human_approval_required": (
            decision_result.action
            == DecisionAction.HUMAN_REVIEW
        ),
        "workflow_status": (
            WorkflowStatus.WAITING_FOR_HUMAN
            if decision_result.action
            == DecisionAction.HUMAN_REVIEW
            else WorkflowStatus.RUNNING
        ),
    }

def human_review_node(
    state: InvoiceAuditState,
    session_factory=SessionLocal,
) -> dict:
    """Pause the workflow and request a human decision."""

    record_workflow_audit_event(
        session_factory=session_factory,
        workflow_id=state["workflow_id"],
        event_type=AuditEventType.HUMAN_REVIEW_REQUESTED,
        idempotency_key=(
            f"human_review_requested:"
            f"{state['workflow_id']}"
        ),
        details={
            "invoice_number": (
                state["invoice"].invoice_number
            ),
            "reasons": (
                state["decision_result"].reasons
            ),
        },
    )

    decision = interrupt(
        {
            "type": "invoice_review",
            "message": (
                "Human approval is required "
                "before continuing."
            ),
            "invoice": state["invoice"].model_dump(
                mode="json"
            ),
            "validation": state[
                "validation_result"
            ].model_dump(mode="json"),
            "reconciliation": state[
                "reconciliation_result"
            ].model_dump(mode="json"),
            "decision": state[
                "decision_result"
            ].model_dump(mode="json"),
        }
    )

    human_decision = HumanDecision(decision)

    event_type = (
        AuditEventType.HUMAN_APPROVED
        if human_decision
        == HumanDecision.APPROVED
        else AuditEventType.HUMAN_REJECTED
    )

    record_workflow_audit_event(
        session_factory=session_factory,
        workflow_id=state["workflow_id"],
        event_type=event_type,
        actor="human",
        idempotency_key=(
            f"{event_type.value}:"
            f"{state['workflow_id']}"
        ),
        details={
            "invoice_number": (
                state["invoice"].invoice_number
            ),
            "decision": human_decision.value,
        },
    )

    return {
        "human_decision": human_decision,
        "workflow_status": (
            WorkflowStatus.RUNNING
            if human_decision
            == HumanDecision.APPROVED
            else WorkflowStatus.REJECTED
        ),
    }


def create_settlement_node(
    session_factory,
):
    """Create a deterministic settlement node."""

    def settlement_node(
        state: InvoiceAuditState,
    ) -> dict:
        """Settle an authorized invoice in the ERP."""

        invoice = state["invoice"]
        workflow_id = state["workflow_id"]
        decision_result = state["decision_result"]

        decision_action = _enum_value(
            decision_result.action
        )

        if decision_action == DecisionAction.HUMAN_REVIEW.value:
            human_decision = _enum_value(
                state.get("human_decision")
            )

            if human_decision != HumanDecision.APPROVED.value:
                raise ValueError(
                    "Invoice is not authorized for settlement."
                )

        elif decision_action != DecisionAction.AUTO_APPROVE.value:
            raise ValueError(
                "Invoice is not authorized for settlement."
            )

        validation_result = state["validation_result"]

        validation_status = _enum_value(
            validation_result.status
        )

        if validation_status != ValidationStatus.PASSED.value:
            raise ValueError(
                "Invoice failed deterministic validation."
            )

        reconciliation_result = state[
            "reconciliation_result"
        ]

        reconciliation_status = _enum_value(
            reconciliation_result.status
        )

        if (
            decision_action == DecisionAction.AUTO_APPROVE.value
            and reconciliation_status
            != ReconciliationStatus.MATCHED.value
        ):
            raise ValueError(
                "Invoice is not safely reconciled "
                "for auto-settlement."
            )

        with ERPUnitOfWork(session_factory) as uow:
            uow.repository.settle_invoice(
                invoice=invoice,
                workflow_id=workflow_id,
            )
            uow.commit()

        return {
            "workflow_status": WorkflowStatus.COMPLETED,
        }

    return settlement_node

def route_after_decision(
    state: InvoiceAuditState,
) -> str:
    """Route the workflow based on the decision result."""

    decision_result = state["decision_result"]

    if decision_result.action == DecisionAction.AUTO_APPROVE:
        return "auto_approve"

    if decision_result.action == DecisionAction.REJECT:
        return "reject"

    return "human_review"


def route_after_human_review(
    state: InvoiceAuditState,
) -> str:
    """Route the workflow after human review."""

    if (
        _enum_value(state.get("human_decision"))
        == HumanDecision.APPROVED.value
    ):
        return "approved"

    return "rejected"


def build_audit_graph(
    erp_tools: ERPTools,
    extraction_pipeline: InvoiceExtractionPipeline | None = None,
    checkpointer=None,
    session_factory=SessionLocal,
):
    """Build the production invoice audit workflow."""

    extraction_pipeline = (
        extraction_pipeline
        or InvoiceExtractionPipeline()
    )

    injected_extraction_node = create_extraction_node(
        extraction_pipeline,
        session_factory=session_factory,
    )

    duplicate_check_node = create_duplicate_check_node(
        erp_tools,
        session_factory=session_factory,
    )

    reconciliation_node = create_reconciliation_node(
        erp_tools,
        session_factory=session_factory,
    )

    settlement_node = create_settlement_node(
        session_factory
    )

    def injected_validation_node(
        state: InvoiceAuditState,
    ) -> dict:
        return validation_node(
            state,
            session_factory=session_factory,
        )

    def injected_decision_node(
        state: InvoiceAuditState,
    ) -> dict:
        return decision_node(
            state,
            session_factory=session_factory,
        )

    def injected_human_review_node(
        state: InvoiceAuditState,
    ) -> dict:
        return human_review_node(
            state,
            session_factory=session_factory,
        )

    graph = StateGraph(InvoiceAuditState)

    graph.add_node(
        "extract",
        injected_extraction_node,
    )

    graph.add_node(
        "validate",
        injected_validation_node,
    )

    graph.add_node(
        "reflect",
        reflection_node,
    )

    graph.add_node(
        "validation_failure",
        validation_failure_node,
    )

    graph.add_node(
        "duplicate_check",
        duplicate_check_node,
    )

    graph.add_node(
        "reconcile",
        reconciliation_node,
    )

    graph.add_node(
        "decide",
        injected_decision_node,
    )

    graph.add_node(
        "human_review",
        injected_human_review_node,
    )

    graph.add_node(
        "settle",
        settlement_node,
    )

    # --------------------------------------------------
    # Main workflow
    # --------------------------------------------------

    graph.add_edge(
        START,
        "extract",
    )

    graph.add_edge(
        "extract",
        "validate",
    )

    # Validation failure -> reflection/retry
    # Validation success -> duplicate check
    graph.add_conditional_edges(
        "validate",
        route_after_validation,
        {
            "passed": "duplicate_check",
            "failed": "reflect",
        },
    )

    # Reflection -> retry extraction or terminate
    graph.add_conditional_edges(
        "reflect",
        route_after_reflection,
        {
            "retry": "extract",
            "stop": "validation_failure",
        },
    )

    # Validation failure -> workflow failure
    graph.add_edge(
        "validation_failure",
        END,
    )


    # Duplicate check -> reconciliation
    graph.add_edge(
        "duplicate_check",
        "reconcile",
    )

    # Reconciliation -> decision
    graph.add_edge(
        "reconcile",
        "decide",
    )

    # Decision -> settlement, human review, or rejection
    graph.add_conditional_edges(
        "decide",
        route_after_decision,
        {
            "auto_approve": "settle",
            "human_review": "human_review",
            "reject": END,
        },
    )

    # Human decision -> settlement or rejection
    graph.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "approved": "settle",
            "rejected": END,
        },
    )

    # Settlement -> workflow completion
    graph.add_edge(
        "settle",
        END,
    )

    return graph.compile(
        checkpointer=checkpointer
    )


def build_graph():
    """Build the invoice extraction and validation workflow."""

    extraction_pipeline = InvoiceExtractionPipeline()

    extraction_node = create_extraction_node(
        extraction_pipeline
    )

    graph = StateGraph(InvoiceAuditState)

    graph.add_node(
        "extract",
        extraction_node,
    )

    graph.add_node(
        "validate",
        validation_node,
    )

    graph.add_node(
        "reflect",
        reflection_node,
    )

    graph.add_edge(
        START,
        "extract",
    )

    graph.add_edge(
        "extract",
        "validate",
    )

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


def build_graph():
    """Build the invoice extraction and validation workflow."""

    extraction_pipeline = InvoiceExtractionPipeline()
    extraction_node = create_extraction_node(
        extraction_pipeline
    )

    graph = StateGraph(InvoiceAuditState)

    graph.add_node(
        "extract",
        extraction_node,
    )

    graph.add_node(
        "validate",
        validation_node,
    )

    graph.add_node(
        "reflect",
        reflection_node,
    )

    graph.add_edge(
        START,
        "extract",
    )

    graph.add_edge(
        "extract",
        "validate",
    )

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

