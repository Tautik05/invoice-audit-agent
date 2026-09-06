from pathlib import Path
import sys

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.extraction.pipeline import InvoiceExtractionPipeline


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python scripts/debug_extraction.py <pdf_path>"
        )

    pdf_path = Path(sys.argv[1])

    if not pdf_path.exists():
        raise SystemExit(
            f"PDF not found: {pdf_path}"
        )

    pipeline = InvoiceExtractionPipeline()

    result = pipeline.process(pdf_path)

    router = pipeline.invoice_extractor.llm_router

    print("\nExtraction metadata:")
    print(f"Provider: {router.last_used_provider}")
    print(f"Model: {router.last_used_model}")

    print("\nExtracted invoice:")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()