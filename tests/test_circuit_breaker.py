from unittest.mock import patch

from app.llm.circuit_breaker import CircuitBreaker


def test_model_is_available_by_default():
    breaker = CircuitBreaker()

    assert breaker.is_available(
        "gemini/gemini-3.6-flash"
    )


def test_open_circuit_makes_model_unavailable():
    breaker = CircuitBreaker()

    model_key = "gemini/gemini-3.6-flash"

    breaker.open(model_key)

    assert not breaker.is_available(
        model_key
    )

    assert breaker.status(model_key) == "open"


def test_reset_closes_circuit():
    breaker = CircuitBreaker()

    model_key = "gemini/gemini-3.6-flash"

    breaker.open(model_key)

    assert not breaker.is_available(
        model_key
    )

    breaker.reset(model_key)

    assert breaker.is_available(
        model_key
    )

    assert breaker.status(model_key) == "closed"


def test_circuit_reopens_after_cooldown_expires():
    breaker = CircuitBreaker(
        cooldown_seconds=300
    )

    model_key = "gemini/gemini-3.6-flash"

    with patch(
        "app.llm.circuit_breaker.monotonic"
    ) as mock_monotonic:

        mock_monotonic.return_value = 100.0

        breaker.open(model_key)

        assert not breaker.is_available(
            model_key
        )

        mock_monotonic.return_value = 400.0

        assert breaker.is_available(
            model_key
        )

        assert breaker.status(model_key) == "closed"


def test_circuits_are_independent():
    breaker = CircuitBreaker()

    gemini_model = (
        "gemini/gemini-3.6-flash"
    )

    groq_model = (
        "groq/qwen/qwen3.6-27b"
    )

    breaker.open(gemini_model)

    assert not breaker.is_available(
        gemini_model
    )

    assert breaker.is_available(
        groq_model
    )

