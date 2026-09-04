from decimal import Decimal
from pathlib import Path

from app.extraction.pipeline import InvoiceExtractionPipeline
from app.schemas.extraction import (
    ExtractedInvoice,
    ExtractedInvoiceLineItem,
)


class FakeDocumentExtractor:
    def extract_text(self, pdf_path: Path) -> str:
        return """
        Invoice Number: INV-TEST-001
        Vendor: Test Vendor
        Currency: USD
        """


class FakeInvoiceExtractor:
    def extract(self, document_text: str) -> ExtractedInvoice:
        return ExtractedInvoice(
            invoice_number="INV-TEST-001",
            vendor="Test Vendor",
            invoice_date=None,
            po_number=None,
            currency="USD",
            line_items=[
                ExtractedInvoiceLineItem(
                    description="Monitor",
                    quantity=1,
                    unit_price="100.00",
                )
            ],
            subtotal="100.00",
            tax_rate="0.18",
            tax="18.00",
            total="118.00",
        )


def test_pipeline_connects_document_and_invoice_extractors(
    tmp_path: Path,
):
    pdf_path = tmp_path / "invoice.pdf"
    pdf_path.write_bytes(b"fake pdf")

    pipeline = InvoiceExtractionPipeline(
        document_extractor=FakeDocumentExtractor(),
        invoice_extractor=FakeInvoiceExtractor(),
    )

    result = pipeline.process(pdf_path)

    assert result.invoice_number == "INV-TEST-001"
    assert result.vendor == "Test Vendor"
    assert result.currency == "USD"
    assert result.line_items[0].quantity == 1
    assert result.line_items[0].unit_price == Decimal("100.00")
    assert result.subtotal == Decimal("100.00")
    assert result.tax_rate == Decimal("0.18")
    assert result.tax == Decimal("18.00")
    assert result.total == Decimal("118.00")