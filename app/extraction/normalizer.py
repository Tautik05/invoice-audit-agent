from app.schemas.extraction import ExtractedInvoice
from app.schemas.invoice import Invoice, InvoiceLineItem


def normalize_invoice(extracted: ExtractedInvoice) -> Invoice:
    return Invoice(
        invoice_number=extracted.invoice_number.strip(),
        vendor=extracted.vendor.strip(),
        invoice_date=extracted.invoice_date,
        po_number=extracted.po_number.strip() if extracted.po_number else None,
        currency=extracted.currency.upper().strip(),
        line_items=[
            InvoiceLineItem(
                description=item.description.strip(),
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in extracted.line_items
        ],
        subtotal=extracted.subtotal,
        tax_rate=extracted.tax_rate,
        tax=extracted.tax,
        total=extracted.total,
    )