from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agent.graph import build_audit_graph
from app.agent.tools.erp_tools import ERPTools
from app.api.routes.health import router as health_router
from app.checkpoint.postgres import postgres_checkpointer
from app.db.session import SessionLocal
from app.erp.service import ERPService
from app.api.routes.invoices import router as invoices_router
from app.api.routes.workflows import router as workflows_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application-wide resources."""

    # Preserve dependencies injected by tests or other application setup.
    if hasattr(app.state, "audit_graph") and hasattr(
        app.state, "session_factory"
    ):
        yield
        return

    erp_service = ERPService.from_session_factory(SessionLocal)

    with postgres_checkpointer() as checkpointer:
        checkpointer.setup()

        app.state.session_factory = SessionLocal
        app.state.audit_graph = build_audit_graph(
            ERPTools(erp_service),
            checkpointer=checkpointer,
            session_factory=SessionLocal,
        )

        yield


app = FastAPI(
    lifespan=lifespan,
    title="Autonomous Invoice Audit & ERP Settlement Agent",
    description=(
        "Production-grade agentic invoice auditing "
        "and ERP settlement system."
    ),
    version="1.0.0",
)

app.include_router(health_router)
app.include_router(invoices_router)
app.include_router(workflows_router)