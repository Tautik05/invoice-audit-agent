from pathlib import Path
from random import Random

from faker import Faker

from app.schemas.synthetic import SyntheticInvoiceRecord
from app.synthetic.rendering import InvoiceRenderer
from scripts.generate_invoices import generate_invoice


def make_invoice() -> SyntheticInvoiceRecord:
    faker = Faker()
    faker.seed_instance(42)

    rng = Random(42)

    return generate_invoice(
        faker=faker,
        rng=rng,
        invoice_number=1,
    )


def test_render_invoice(tmp_path: Path):
    invoice = make_invoice()

    renderer = InvoiceRenderer(
        output_directory=tmp_path
    )

    output_path = renderer.render(invoice)

    assert output_path.exists()
    assert output_path.name == "INV-00001.pdf"
    assert output_path.stat().st_size > 0


def test_renderer_produces_multiple_templates(tmp_path: Path):
    faker = Faker()
    faker.seed_instance(42)

    invoices = [
        generate_invoice(
            faker=faker,
            rng=Random(index),
            invoice_number=index,
        )
        for index in range(1, 8)
    ]

    renderer = InvoiceRenderer(output_directory=tmp_path)

    output_paths = [
        renderer.render(invoice)
        for invoice in invoices
    ]

    assert len(output_paths) == 7

    for output_path in output_paths:
        assert output_path.exists()
        assert output_path.stat().st_size > 0