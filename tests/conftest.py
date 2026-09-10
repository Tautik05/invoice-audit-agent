from collections.abc import Callable, Generator

from decimal import Decimal

import os

from dotenv import load_dotenv

import app.db.models  # noqa: F401

import pytest

from sqlalchemy import create_engine, delete, select

from sqlalchemy.pool import StaticPool

from sqlalchemy.orm import Session

from app.db.models.invoice import Invoice as InvoiceModel

from app.db.models.purchase_order import (
    PurchaseOrder as PurchaseOrderModel,
)
from app.db.models.audit_event import AuditEvent

from app.db.base import Base

from app.erp.repository import ERPRepository

from app.erp.service import ERPService

from app.schemas.purchase_order import (
    PurchaseOrder as PurchaseOrderSchema,
    PurchaseOrderLineItem,
)

from app.db.models.vendor import Vendor as VendorModel

from app.schemas.vendor import Vendor as VendorSchema

from app.db.models.invoice_line_item import (
    InvoiceLineItem as InvoiceLineItemModel,
)

from app.db.models.purchase_order_item import (
    PurchaseOrderItem as PurchaseOrderItemModel,
)


load_dotenv()


@pytest.fixture
def db_engine():
    """Create an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()


@pytest.fixture
def db_session(
    db_engine,
) -> Generator[Session, None, None]:
    """Provide an isolated database session."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture
def session_factory(
    db_engine,
) -> Callable[[], Session]:
    """Create fresh sessions against the same test database."""

    def factory() -> Session:
        return Session(db_engine)

    return factory


@pytest.fixture
def erp_service(
    db_session: Session,
) -> ERPService:
    """Create an ERP service with isolated test data."""

    repository = ERPRepository(db_session)

    repository.add_vendor(
        VendorSchema(
            vendor_id="V-001",
            name="ABC Supplies",
            currency="USD",
        )
    )

    repository.add_vendor(
        VendorSchema(
            vendor_id="V-002",
            name="Acme Corp",
            currency="USD",
        )
    )

    repository.add_purchase_order(
        PurchaseOrderSchema(
            po_number="PO-8821",
            vendor="ABC Supplies",
            currency="USD",
            line_items=[
                PurchaseOrderLineItem(
                    description="Monitor",
                    quantity=10,
                    unit_price=Decimal("200.00"),
                )
            ],
            subtotal=Decimal("2000.00"),
            tax_rate=Decimal("0.18"),
            tax=Decimal("360.00"),
            total=Decimal("2360.00"),
        )
    )

    repository.add_purchase_order(
        PurchaseOrderSchema(
            po_number="PO-9941",
            vendor="Acme Corp",
            currency="USD",
            line_items=[
                PurchaseOrderLineItem(
                    description="Laptop",
                    quantity=5,
                    unit_price=Decimal("800.00"),
                )
            ],
            subtotal=Decimal("4000.00"),
            tax_rate=Decimal("0.18"),
            tax=Decimal("720.00"),
            total=Decimal("4720.00"),
        )
    )

    db_session.commit()

    return ERPService(repository)


@pytest.fixture
def seeded_database(
    db_session: Session,
) -> None:
    """Seed the test database with ERP reference data."""

    repository = ERPRepository(db_session)

    repository.add_vendor(
        VendorSchema(
            vendor_id="V-001",
            name="ABC Supplies",
            currency="USD",
        )
    )

    repository.add_purchase_order(
        PurchaseOrderSchema(
            po_number="PO-8821",
            vendor="ABC Supplies",
            currency="USD",
            line_items=[
                PurchaseOrderLineItem(
                    description="Monitor",
                    quantity=10,
                    unit_price=Decimal("200.00"),
                )
            ],
            subtotal=Decimal("2000.00"),
            tax_rate=Decimal("0.18"),
            tax=Decimal("360.00"),
            total=Decimal("2360.00"),
        )
    )

    db_session.commit()


@pytest.fixture
def postgres_session_factory():
    """Create independent PostgreSQL sessions for concurrency tests."""

    database_url = os.getenv(
        "DATABASE_URL_UNPOOLED"
    )

    if not database_url:
        pytest.skip(
            "DATABASE_URL_UNPOOLED is not configured."
        )

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    def factory() -> Session:
        return Session(engine)

    yield factory

    engine.dispose()


@pytest.fixture
def seeded_postgres_database(
    postgres_session_factory,
):
    """Seed isolated ERP reference data in PostgreSQL."""

    with postgres_session_factory() as session:
        repository = ERPRepository(session)

        repository.add_vendor(
            VendorSchema(
                vendor_id="V-CONCURRENCY-001",
                name="ABC Supplies",
                currency="USD",
            )
        )

        repository.add_purchase_order(
            PurchaseOrderSchema(
                po_number="PO-CONCURRENCY-001",
                vendor="ABC Supplies",
                currency="USD",
                line_items=[
                    PurchaseOrderLineItem(
                        description="Monitor",
                        quantity=1,
                        unit_price=Decimal("200.00"),
                    )
                ],
                subtotal=Decimal("200.00"),
                tax_rate=Decimal("0.18"),
                tax=Decimal("36.00"),
                total=Decimal("236.00"),
            )
        )

        session.commit()

    yield

    # Clean up test data after the test.
    # Clean up test data after the test.
    with postgres_session_factory() as session:
        vendor = session.scalar(
            select(VendorModel).where(
                VendorModel.vendor_code
                == "V-CONCURRENCY-001"
            )
        )

        purchase_order = session.scalar(
            select(PurchaseOrderModel).where(
                PurchaseOrderModel.po_number
                == "PO-CONCURRENCY-001"
            )
        )

        session.execute(
            delete(AuditEvent).where(
                AuditEvent.workflow_id
                == "workflow-concurrency-001"
            )
        )

        if vendor is not None:
            session.execute(
                delete(InvoiceLineItemModel).where(
                    InvoiceLineItemModel.invoice_id.in_(
                        select(InvoiceModel.id).where(
                            InvoiceModel.vendor_id == vendor.id
                        )
                    )
                )
            )

            session.execute(
                delete(InvoiceModel).where(
                    InvoiceModel.vendor_id == vendor.id
                )
            )

        if purchase_order is not None:
            session.execute(
                delete(PurchaseOrderItemModel).where(
                    PurchaseOrderItemModel.purchase_order_id
                    == purchase_order.id
                )
            )

            session.execute(
                delete(PurchaseOrderModel).where(
                    PurchaseOrderModel.id
                    == purchase_order.id
                )
            )

        if vendor is not None:
            session.execute(
                delete(VendorModel).where(
                    VendorModel.id == vendor.id
                )
            )

        session.commit()