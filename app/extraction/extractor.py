from app.extraction.response_normalizer import (
    normalize_extraction_response,
)
from app.llm.router import LLMRouter
from app.llm.router_config import create_llm_router
from app.schemas.extraction import ExtractedInvoice


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
        feedback: str | None = None,
    ) -> ExtractedInvoice:
        prompt = f"""
Extract the invoice information from the document below.

Return the result as valid JSON matching the requested schema.

Rules:
- Extract only information explicitly present in the document.
- Do not correct mathematical errors in the invoice.
- Preserve values as printed unless normalization is required by the schema.
- Do not infer or fabricate missing information.
- For optional identifiers such as purchase order numbers, return null
  when the document indicates the value is unavailable, such as N/A,
  NA, None, or a dash.
- If a field is not present or explicitly unavailable, return null
  where permitted.
"""

        if feedback:
            prompt += f"""
Previous extraction attempt failed deterministic validation.

Use the following feedback to re-examine the source document:

{feedback}

Important:
- Re-examine the original document carefully.
- Extract the values actually printed in the document.
- Do not mathematically correct the invoice.
- Do not change a value merely because it appears financially unusual.
"""

        prompt += f"""
Document:
{document_text}
"""

        response_text = self.llm_router.generate_structured(
            prompt=prompt,
            response_schema=ExtractedInvoice,
        )

        return normalize_extraction_response(
            response_text
        )