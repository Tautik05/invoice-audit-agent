from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.invoice import Invoice
    from app.db.models.purchase_order import PurchaseOrder


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    vendor_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    purchase_orders: Mapped[list["PurchaseOrder"]] = relationship(
        back_populates="vendor",
    )

    invoices: Mapped[list["Invoice"]] = relationship(
        back_populates="vendor",
    )