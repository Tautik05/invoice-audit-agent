from app.llm.router import LLMRouter
from app.llm.router_config import create_llm_router
from app.schemas.extraction import ExtractedInvoice

from app.extraction.response_normalizer import (
    normalize_extraction_response,
)

class InvoiceExtractor:
    """Extract structured invoice data using an LLM router."""

    def __init__(
        self,
        llm_router: LLMRouter | None = None,
    ) -> None:
        self.llm_router = (
            llm_router
            or create_llm_router()
        )

    def extract(
        self,
        document_text: str,
    ) -> ExtractedInvoice:
        prompt = f"""
Extract the invoice information from the document below.

Return the result as valid JSON matching the requested schema.

Rules:
- Extract only information explicitly present in the document.
- Do not correct mathematical errors in the invoice.
- Preserve the values exactly as printed.
- Do not infer missing information.
- If a field is not present, return null where permitted.

Document:
{document_text}
"""

        response_text = (
            self.llm_router.generate_structured(
                prompt=prompt,
                response_schema=ExtractedInvoice,
            )
        )

        return normalize_extraction_response(
            response_text
        )

