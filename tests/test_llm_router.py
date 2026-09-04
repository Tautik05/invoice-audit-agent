import pytest

from app.llm.errors import (
    LLMError,
    LLMErrorType,
)
from app.llm.router import (
    LLMRouter,
    ModelConfig,
)
from app.llm.retry import RetryPolicy


class FakeProvider:
    """Fake provider used to test router behavior."""

    def __init__(
        self,
        responses: list[str | Exception],
    ) -> None:
        self.responses = responses
        self.calls = 0

    def generate_structured(
        self,
        prompt: str,
        response_schema,
    ) -> str:
        response = self.responses[
            min(
                self.calls,
                len(self.responses) - 1,
            )
        ]

        self.calls += 1

        if isinstance(response, Exception):
            raise response

        return response


def make_error(
    error_type: LLMErrorType,
    retryable: bool,
    provider: str = "test",
    model: str = "test-model",
) -> LLMError:
    return LLMError(
        message="test error",
        error_type=error_type,
        provider=provider,
        model=model,
        retryable=retryable,
    )


def test_router_returns_successful_response():
    provider = FakeProvider(
        responses=['{"invoice_number": "INV-001"}']
    )

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="test",
                model="model-a",
            )
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
    )

    router._create_provider = (
        lambda config: provider
    )

    result = router.generate_structured(
        prompt="test",
        response_schema=dict,
    )

    assert result == (
        '{"invoice_number": "INV-001"}'
    )

    assert provider.calls == 1


def test_router_retries_transient_error():
    provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.TRANSIENT,
                retryable=True,
            ),
            '{"invoice_number": "INV-001"}',
        ]
    )

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="test",
                model="model-a",
            )
        ],
        retry_policy=RetryPolicy(
            max_attempts=2,
            initial_delay=0,
        ),
    )

    router._create_provider = (
        lambda config: provider
    )

    result = router.generate_structured(
        prompt="test",
        response_schema=dict,
    )

    assert result == (
        '{"invoice_number": "INV-001"}'
    )

    assert provider.calls == 2


def test_router_falls_back_after_quota_exhaustion():
    first_provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.QUOTA_EXHAUSTED,
                retryable=False,
                provider="gemini",
                model="gemini-3.6-flash",
            )
        ]
    )

    second_provider = FakeProvider(
        responses=[
            '{"invoice_number": "INV-001"}'
        ]
    )

    providers = {
        "gemini-3.6-flash": first_provider,
        "gemini-3.7-flash": second_provider,
    }

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="gemini",
                model="gemini-3.6-flash",
            ),
            ModelConfig(
                provider="gemini",
                model="gemini-3.7-flash",
            ),
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
    )

    router._create_provider = (
        lambda config: providers[config.model]
    )

    result = router.generate_structured(
        prompt="test",
        response_schema=dict,
    )

    assert result == (
        '{"invoice_number": "INV-001"}'
    )

    assert first_provider.calls == 1
    assert second_provider.calls == 1


def test_router_falls_back_to_groq():
    gemini_provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.TRANSIENT,
                retryable=True,
                provider="gemini",
                model="gemini-3.6-flash",
            )
        ]
    )

    groq_provider = FakeProvider(
        responses=[
            '{"invoice_number": "INV-001"}'
        ]
    )

    providers = {
        "gemini-3.6-flash": gemini_provider,
        "qwen/qwen3.6-27b": groq_provider,
    }

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="gemini",
                model="gemini-3.6-flash",
            ),
            ModelConfig(
                provider="groq",
                model="qwen/qwen3.6-27b",
            ),
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
    )

    router._create_provider = (
        lambda config: providers[config.model]
    )

    result = router.generate_structured(
        prompt="test",
        response_schema=dict,
    )

    assert result == (
        '{"invoice_number": "INV-001"}'
    )

    assert gemini_provider.calls == 1
    assert groq_provider.calls == 1


def test_router_stops_on_authentication_error():
    provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.AUTHENTICATION,
                retryable=False,
                provider="gemini",
                model="gemini-3.6-flash",
            )
        ]
    )

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="gemini",
                model="gemini-3.6-flash",
            ),
            ModelConfig(
                provider="groq",
                model="qwen/qwen3.6-27b",
            ),
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
    )

    router._create_provider = (
        lambda config: provider
    )

    with pytest.raises(LLMError) as exc_info:
        router.generate_structured(
            prompt="test",
            response_schema=dict,
        )

    assert (
        exc_info.value.error_type
        == LLMErrorType.AUTHENTICATION
    )

    assert provider.calls == 1


def test_router_raises_when_all_providers_fail():
    first_provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.TRANSIENT,
                retryable=False,
                provider="gemini",
                model="gemini-3.6-flash",
            )
        ]
    )

    second_provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.UNKNOWN,
                retryable=False,
                provider="groq",
                model="qwen/qwen3.6-27b",
            )
        ]
    )

    providers = {
        "gemini-3.6-flash": first_provider,
        "qwen/qwen3.6-27b": second_provider,
    }

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="gemini",
                model="gemini-3.6-flash",
            ),
            ModelConfig(
                provider="groq",
                model="qwen/qwen3.6-27b",
            ),
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
    )

    router._create_provider = (
        lambda config: providers[config.model]
    )

    with pytest.raises(RuntimeError) as exc_info:
        router.generate_structured(
            prompt="test",
            response_schema=dict,
        )

    assert "All configured LLM providers failed" in (
        str(exc_info.value)
    )

    assert first_provider.calls == 1
    assert second_provider.calls == 1

def test_router_opens_circuit_after_quota_exhaustion():
    from app.llm.circuit_breaker import (
        CircuitBreaker,
    )

    provider = FakeProvider(
        responses=[
            make_error(
                LLMErrorType.QUOTA_EXHAUSTED,
                retryable=False,
                provider="gemini",
                model="gemini-3.6-flash",
            )
        ]
    )

    fallback_provider = FakeProvider(
        responses=[
            '{"invoice_number": "INV-001"}'
        ]
    )

    providers = {
        "gemini-3.6-flash": provider,
        "gemini-3.7-flash": fallback_provider,
    }

    breaker = CircuitBreaker(
        cooldown_seconds=300
    )

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="gemini",
                model="gemini-3.6-flash",
            ),
            ModelConfig(
                provider="gemini",
                model="gemini-3.7-flash",
            ),
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
        circuit_breaker=breaker,
    )

    router._create_provider = (
        lambda config: providers[config.model]
    )

    result = router.generate_structured(
        prompt="test",
        response_schema=dict,
    )

    assert result == (
        '{"invoice_number": "INV-001"}'
    )

    assert not breaker.is_available(
        "gemini/gemini-3.6-flash"
    )


def test_router_skips_model_with_open_circuit():
    from app.llm.circuit_breaker import (
        CircuitBreaker,
    )

    first_provider = FakeProvider(
        responses=[
            '{"invoice_number": "SHOULD-NOT-BE-CALLED"}'
        ]
    )

    fallback_provider = FakeProvider(
        responses=[
            '{"invoice_number": "INV-001"}'
        ]
    )

    providers = {
        "gemini-3.6-flash": first_provider,
        "gemini-3.7-flash": fallback_provider,
    }

    breaker = CircuitBreaker()

    breaker.open(
        "gemini/gemini-3.6-flash"
    )

    router = LLMRouter(
        models=[
            ModelConfig(
                provider="gemini",
                model="gemini-3.6-flash",
            ),
            ModelConfig(
                provider="gemini",
                model="gemini-3.7-flash",
            ),
        ],
        retry_policy=RetryPolicy(
            max_attempts=1,
            initial_delay=0,
        ),
        circuit_breaker=breaker,
    )

    router._create_provider = (
        lambda config: providers[config.model]
    )

    result = router.generate_structured(
        prompt="test",
        response_schema=dict,
    )

    assert result == (
        '{"invoice_number": "INV-001"}'
    )

    assert first_provider.calls == 0
    assert fallback_provider.calls == 1

