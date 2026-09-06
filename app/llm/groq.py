from typing import Any

from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    BadRequestError,
    Groq,
    RateLimitError,
)

from app.config import settings
from app.llm.errors import LLMError, LLMErrorType
from app.llm.provider import LLMProvider


class GroqProvider(LLMProvider):
    """Groq-based structured-output provider."""

    def __init__(self, model: str) -> None:
        if not settings.groq_api_key:
            raise ValueError(
                "GROQ_API_KEY is not set."
            )

        self.client = Groq(
            api_key=settings.groq_api_key,
            max_retries=0,
        )

        self.model = model

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
    ) -> str:
        try:
            response = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt,
                        }
                    ],
                    response_format={
                        "type": "json_object"
                    },
                )
            )

            content = (
                response.choices[0]
                .message
                .content
            )

            if not content:
                raise LLMError(
                    message=(
                        "Groq returned an empty "
                        "response."
                    ),
                    error_type=(
                        LLMErrorType.UNKNOWN
                    ),
                    provider="groq",
                    model=self.model,
                    retryable=False,
                )

            return content

        except RateLimitError as exc:
            raise self._classify_rate_limit_error(
                exc
            ) from exc

        except AuthenticationError as exc:
            raise LLMError(
                message=str(exc),
                error_type=(
                    LLMErrorType.AUTHENTICATION
                ),
                provider="groq",
                model=self.model,
                retryable=False,
            ) from exc

        except BadRequestError as exc:
            raise LLMError(
                message=str(exc),
                error_type=(
                    LLMErrorType.INVALID_REQUEST
                ),
                provider="groq",
                model=self.model,
                retryable=False,
            ) from exc

        except APIConnectionError as exc:
            raise LLMError(
                message=str(exc),
                error_type=(
                    LLMErrorType.TRANSIENT
                ),
                provider="groq",
                model=self.model,
                retryable=True,
            ) from exc

        except APIStatusError as exc:
            raise self._classify_status_error(
                exc
            ) from exc

    def _classify_rate_limit_error(
        self,
        exc: RateLimitError,
    ) -> LLMError:
        message = str(exc).lower()

        if any(
            keyword in message
            for keyword in (
                "daily",
                "requests per day",
                "rpd",
                "tokens per day",
                "tpd",
            )
        ):
            error_type = (
                LLMErrorType.QUOTA_EXHAUSTED
            )
            retryable = False

        else:
            error_type = (
                LLMErrorType.RATE_LIMIT
            )
            retryable = True

        return LLMError(
            message=str(exc),
            error_type=error_type,
            provider="groq",
            model=self.model,
            retryable=retryable,
        )

    def _classify_status_error(
        self,
        exc: APIStatusError,
    ) -> LLMError:
        if exc.status_code in {
            500,
            502,
            503,
            504,
        }:
            error_type = (
                LLMErrorType.TRANSIENT
            )
            retryable = True

        elif exc.status_code == 429:
            error_type = (
                LLMErrorType.RATE_LIMIT
            )
            retryable = True

        else:
            error_type = (
                LLMErrorType.UNKNOWN
            )
            retryable = False

        return LLMError(
            message=str(exc),
            error_type=error_type,
            provider="groq",
            model=self.model,
            retryable=retryable,
        )