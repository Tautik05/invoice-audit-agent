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
    ) -> ExtractedInvoice:
        prompt = f"""
Extract the invoice information from the document below.

Rules:
- Extract only information explicitly present in the document.
- Do not invent missing values.
- Preserve the invoice's monetary values.
- Extract every invoice line item.
- Return the tax rate as a decimal fraction.
  For example, 18% should become 0.18.
- Currency must be a three-letter ISO currency code.

Invoice document:

{document_text}
"""

        response_text = (
            self.llm_router.generate_structured(
                prompt=prompt,
                response_schema=ExtractedInvoice,
            )
        )

        return ExtractedInvoice.model_validate_json(
            response_text
        )

