from dataclasses import dataclass
from typing import Any

from app.llm.circuit_breaker import CircuitBreaker
from app.llm.client import GeminiProvider
from app.llm.errors import LLMError, LLMErrorType
from app.llm.groq import GroqProvider
from app.llm.provider import LLMProvider
from app.llm.retry import RetryPolicy


@dataclass
class ModelConfig:
    provider: str
    model: str


class LLMRouter:
    """Routes requests across configured LLM providers."""

    def __init__(
        self,
        models: list[ModelConfig],
        retry_policy: RetryPolicy | None = None,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.models = models

        self.retry_policy = (
            retry_policy
            or RetryPolicy()
        )

        self.circuit_breaker = (
            circuit_breaker
            or CircuitBreaker()
        )

    def _create_provider(
        self,
        config: ModelConfig,
    ) -> LLMProvider:
        if config.provider == "gemini":
            return GeminiProvider(
                config.model
            )

        if config.provider == "groq":
            return GroqProvider(
                config.model
            )

        raise ValueError(
            f"Unsupported provider: "
            f"{config.provider}"
        )

    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
    ) -> str:
        errors: list[str] = []

        for config in self.models:
            model_key = (
                f"{config.provider}/"
                f"{config.model}"
            )

            # Skip models whose circuit is open.
            if not self.circuit_breaker.is_available(
                model_key
            ):
                print(
                    f"Skipping {model_key}: "
                    "circuit is open."
                )

                continue

            try:
                provider = (
                    self._create_provider(config)
                )

                result = (
                    self.retry_policy.execute(
                        lambda: (
                            provider.generate_structured(
                                prompt=prompt,
                                response_schema=response_schema,
                            )
                        )
                    )
                )

                # Successful request means the
                # provider is healthy again.
                self.circuit_breaker.reset(
                    model_key
                )

                return result

            except LLMError as exc:
                errors.append(
                    f"{exc.provider}/{exc.model}: "
                    f"{exc.error_type.value} - "
                    f"{exc.message}"
                )

                if (
                    exc.error_type
                    == LLMErrorType.QUOTA_EXHAUSTED
                ):
                    self.circuit_breaker.open(
                        model_key
                    )

                    print(
                        f"Opening circuit for "
                        f"{model_key}."
                    )

                    continue

                if (
                    exc.error_type
                    == LLMErrorType.AUTHENTICATION
                ):
                    raise

                if (
                    exc.error_type
                    == LLMErrorType.INVALID_REQUEST
                ):
                    raise

                continue

        raise RuntimeError(
            "All configured LLM providers failed:\n"
            + "\n".join(errors)
        )

