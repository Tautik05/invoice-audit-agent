from pathlib import Path

from faker import Faker

from app.extraction.document import PDFTextExtractor
from app.synthetic.rendering import InvoiceRenderer
from scripts.generate_invoices import generate_invoice

from random import Random
import pytest

def make_invoice():
    faker = Faker()
    faker.seed_instance(42)

    return generate_invoice(
        faker=faker,
        rng=Random(42),
        invoice_number=1,
    )


def test_extract_text_from_pdf(tmp_path: Path):
    invoice = make_invoice()

    renderer = InvoiceRenderer(output_directory=tmp_path)
    pdf_path = renderer.render(invoice)

    extractor = PDFTextExtractor()

    text = extractor.extract_text(pdf_path)

    assert text
    assert "INV-00001" in text
    assert invoice.vendor in text
    assert invoice.currency in text
    assert str(invoice.total) in text

def test_extract_text_raises_for_missing_file(tmp_path: Path):
    extractor = PDFTextExtractor()

    with pytest.raises(FileNotFoundError):
        extractor.extract_text(tmp_path / "missing.pdf")


def test_extract_text_rejects_non_pdf(tmp_path: Path):
    extractor = PDFTextExtractor()

    text_file = tmp_path / "invoice.txt"
    text_file.write_text("not a PDF", encoding="utf-8")

    with pytest.raises(ValueError):
        extractor.extract_text(text_file)