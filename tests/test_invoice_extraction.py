from decimal import Decimal

from app.extraction.extractor import InvoiceExtractor


def test_extract_invoice_from_text():
    document_text = """
    INVOICE

    Invoice Number: INV-1001
    Vendor: ABC Supplies
    Invoice Date: 2026-09-01
    Purchase Order: PO-8821

    Currency: USD

    Items:
    Monitor - Quantity: 10 - Unit Price: $200.00

    Subtotal: $2,000.00
    Tax: 18%
    Tax Amount: $360.00
    Total: $2,360.00
    """

    extractor = InvoiceExtractor()
    invoice = extractor.extract(document_text)

    assert invoice.invoice_number == "INV-1001"
    assert invoice.vendor == "ABC Supplies"
    assert invoice.po_number == "PO-8821"
    assert invoice.currency == "USD"

    assert len(invoice.line_items) == 1
    assert invoice.line_items[0].description == "Monitor"
    assert invoice.line_items[0].quantity == 10
    assert invoice.line_items[0].unit_price == Decimal("200.00")

    assert invoice.subtotal == Decimal("2000.00")
    assert invoice.tax_rate == Decimal("0.18")
    assert invoice.tax == Decimal("360.00")
    assert invoice.total == Decimal("2360.00")