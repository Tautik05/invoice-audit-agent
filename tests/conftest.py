from collections.abc import Callable, Generator
from decimal import Decimal

import app.db.models  # noqa: F401
import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.db.base import Base
from app.erp.repository import ERPRepository
from app.erp.service import ERPService
from app.schemas.purchase_order import (
    PurchaseOrder as PurchaseOrderSchema,
    PurchaseOrderLineItem,
)
from app.schemas.vendor import Vendor as VendorSchema


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