from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


if TYPE_CHECKING:
    from app.db.models.invoice_line_item import InvoiceLineItem
    from app.db.models.vendor import Vendor


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    invoice_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    vendor_id: Mapped[int] = mapped_column(
        ForeignKey("vendors.id"),
        nullable=False,
        index=True,
    )

    po_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )

    invoice_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 6),
        nullable=False,
    )

    tax: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    total: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="received",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    vendor: Mapped["Vendor"] = relationship(
        back_populates="invoices",
    )

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice",
        cascade="all, delete-orphan",
    )