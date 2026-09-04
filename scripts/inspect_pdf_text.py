from pathlib import Path
import sys
sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
    )
)

from app.extraction.document import PDFTextExtractor


PDF_DIRECTORY = Path("data/synthetic/documents")


def main() -> None:
    extractor = PDFTextExtractor()

    for index in range(1, 8):
        pdf_path = PDF_DIRECTORY / f"INV-{index:05d}.pdf"

        text = extractor.extract_text(pdf_path)

        print("\n")
        print("=" * 80)
        print(f"{pdf_path.name}")
        print("=" * 80)
        print(text)


if __name__ == "__main__":
    main()