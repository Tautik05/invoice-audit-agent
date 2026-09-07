from decimal import Decimal

from app.schemas.enums import ReconciliationStatus
from app.schemas.invoice import Invoice
from app.schemas.purchase_order import PurchaseOrder
from app.schemas.reconciliation import ReconciliationResult


MONEY_TOLERANCE = Decimal("0.01")


def amounts_match(
    expected: Decimal,
    actual: Decimal,
) -> bool:
    """Check whether two monetary values are within tolerance."""
    return abs(expected - actual) <= MONEY_TOLERANCE


def line_items_match(
    invoice: Invoice,
    purchase_order: PurchaseOrder,
) -> bool:
    """Compare invoice and PO line items deterministically."""
    if len(invoice.line_items) != len(
        purchase_order.line_items
    ):
        return False

    for invoice_item, po_item in zip(
        invoice.line_items,
        purchase_order.line_items,
    ):
        if invoice_item.description.strip().lower() != (
            po_item.description.strip().lower()
        ):
            return False

        if invoice_item.quantity != po_item.quantity:
            return False

        if not amounts_match(
            invoice_item.unit_price,
            po_item.unit_price,
        ):
            return False

    return True


def reconcile_invoice(
    invoice: Invoice,
    purchase_order: PurchaseOrder | None,
) -> ReconciliationResult:
    """Reconcile an invoice against an ERP purchase order."""

    if purchase_order is None:
        return ReconciliationResult(
            status=ReconciliationStatus.NOT_FOUND,
            po_found=False,
            vendor_matched=False,
            currency_matched=False,
            line_items_matched=False,
            invoice_total=invoice.total,
            errors=[
                f"Purchase order not found: {invoice.po_number}"
            ],
        )

    vendor_matched = (
        invoice.vendor.strip().lower()
        == purchase_order.vendor.strip().lower()
    )

    currency_matched = (
        invoice.currency.upper()
        == purchase_order.currency.upper()
    )

    items_matched = line_items_match(
        invoice,
        purchase_order,
    )

    variance = invoice.total - purchase_order.total

    errors: list[str] = []

    if not vendor_matched:
        errors.append(
            "Invoice vendor does not match the purchase order vendor."
        )

    if not currency_matched:
        errors.append(
            "Invoice currency does not match the purchase order currency."
        )

    if not items_matched:
        errors.append(
            "Invoice line items do not match the purchase order."
        )

    if not amounts_match(
        invoice.total,
        purchase_order.total,
    ):
        errors.append(
            "Invoice total does not match the purchase order total."
        )

    if errors:
        status = ReconciliationStatus.VARIANCE
    else:
        status = ReconciliationStatus.MATCHED

    return ReconciliationResult(
        status=status,
        po_found=True,
        vendor_matched=vendor_matched,
        currency_matched=currency_matched,
        line_items_matched=items_matched,
        invoice_total=invoice.total,
        po_total=purchase_order.total,
        variance=variance,
        errors=errors,
    )