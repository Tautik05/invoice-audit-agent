from pathlib import Path

from app.extraction.document import PDFTextExtractor
from app.extraction.extractor import InvoiceExtractor
from app.llm.router_config import create_llm_router
from app.schemas.extraction import ExtractedInvoice


class InvoiceExtractionPipeline:
    """Run the complete PDF-to-structured-invoice extraction pipeline."""

    def __init__(
        self,
        document_extractor: PDFTextExtractor | None = None,
        invoice_extractor: InvoiceExtractor | None = None,
    ) -> None:
        self.document_extractor = (
            document_extractor or PDFTextExtractor()
        )
        self.invoice_extractor = (
            invoice_extractor
            or InvoiceExtractor(
                llm_router=create_llm_router()
            )
        )

    def process(
        self,
        pdf_path: Path,
        feedback: str | None = None,
    ) -> ExtractedInvoice:
        """Run the complete PDF-to-structured-invoice extraction pipeline."""
        document_text = self.document_extractor.extract_text(
            pdf_path
        )

        if not document_text:
            raise ValueError(
                f"No text could be extracted from PDF: {pdf_path}"
            )

        return self.invoice_extractor.extract(
            document_text,
            feedback=feedback,
        )