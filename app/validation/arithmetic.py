from decimal import Decimal, ROUND_HALF_UP

from app.schemas.invoice import Invoice


MONEY_QUANTIZER = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    """Round a monetary value to two decimal places."""
    return value.quantize(MONEY_QUANTIZER, rounding=ROUND_HALF_UP)


def calculate_subtotal(invoice: Invoice) -> Decimal:
    """Calculate subtotal from invoice line items."""
    subtotal = sum(
        (
            item.quantity * item.unit_price
            for item in invoice.line_items
        ),
        Decimal("0"),
    )

    return quantize_money(subtotal)


def calculate_tax(invoice: Invoice) -> Decimal:
    """Calculate tax from the calculated subtotal and tax rate."""
    subtotal = calculate_subtotal(invoice)

    tax = subtotal * invoice.tax_rate

    return quantize_money(tax)


def calculate_total(invoice: Invoice) -> Decimal:
    """Calculate total from calculated subtotal and tax."""
    subtotal = calculate_subtotal(invoice)
    tax = calculate_tax(invoice)

    return quantize_money(subtotal + tax)