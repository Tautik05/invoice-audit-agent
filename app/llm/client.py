from typing import Any

from google import genai
from google.genai import types
from google.genai.errors import ClientError, ServerError

from app.config import settings
from app.llm.errors import LLMError, LLMErrorType
from app.llm.provider import LLMProvider


class GeminiProvider(LLMProvider):
    """Gemini-based structured-output provider."""

    def __init__(self, model: str) -> None:
        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )
        self.model = model

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
    ) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )

            return response.text

        except ServerError as exc:
            raise self._classify_server_error(exc) from exc

        except ClientError as exc:
            raise self._classify_client_error(exc) from exc

    def _classify_server_error(
        self,
        exc: ServerError,
    ) -> LLMError:
        if exc.code in {500, 502, 503, 504}:
            return LLMError(
                message=str(exc),
                error_type=LLMErrorType.TRANSIENT,
                provider="gemini",
                model=self.model,
                retryable=True,
            )

        return LLMError(
            message=str(exc),
            error_type=LLMErrorType.UNKNOWN,
            provider="gemini",
            model=self.model,
        )

    def _classify_client_error(
        self,
        exc: ClientError,
    ) -> LLMError:
        if exc.code == 401:
            error_type = LLMErrorType.AUTHENTICATION

        elif exc.code == 404:
            error_type = LLMErrorType.MODEL_NOT_FOUND

        elif exc.code == 400:
            error_type = LLMErrorType.INVALID_REQUEST

        elif exc.code == 429:
            message = str(exc).lower()

            if any(
                keyword in message
                for keyword in (
                    "daily",
                    "quota",
                    "requests per day",
                    "rpd",
                )
            ):
                error_type = LLMErrorType.QUOTA_EXHAUSTED
            else:
                error_type = LLMErrorType.RATE_LIMIT

        else:
            error_type = LLMErrorType.UNKNOWN

        retryable = error_type in {
            LLMErrorType.TRANSIENT,
            LLMErrorType.RATE_LIMIT,
        }

        return LLMError(
            message=str(exc),
            error_type=error_type,
            provider="gemini",
            model=self.model,
            retryable=retryable,
        )


class GeminiClient:
    """
    Backward-compatible Gemini client.

    The application uses GeminiProvider through LLMRouter.
    This wrapper preserves the older GeminiClient interface
    for existing tests and code.
    """

    def __init__(self) -> None:
        self.provider = GeminiProvider(
            settings.gemini_model
        )

        # Preserve the old public interface.
        self.client = self.provider.client
        self.model = self.provider.model

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
    ) -> str:
        return self.provider.generate_structured(
            prompt=prompt,
            response_schema=response_schema,
        )

