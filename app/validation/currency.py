from app.schemas.invoice import Invoice


SUPPORTED_CURRENCIES = {
    "USD",
    "EUR",
    "GBP",
    "INR",
}


def validate_currency(invoice: Invoice) -> bool:
    """Validate that the invoice uses a supported currency."""
    return invoice.currency.upper() in SUPPORTED_CURRENCIES