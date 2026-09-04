from dataclasses import dataclass
from time import monotonic


@dataclass
class CircuitState:
    """Track the state of a single model circuit."""

    is_open: bool = False
    opened_at: float | None = None


class CircuitBreaker:
    """
    Prevent repeated calls to an unavailable LLM model.

    The circuit can be opened for a configured amount of time.
    Once the cooldown expires, the circuit allows another attempt.
    """

    def __init__(
        self,
        cooldown_seconds: float = 300.0,
    ) -> None:
        self.cooldown_seconds = cooldown_seconds
        self._circuits: dict[str, CircuitState] = {}

    def is_available(
        self,
        model_key: str,
    ) -> bool:
        """Return whether a model is currently available."""

        state = self._circuits.get(model_key)

        if state is None:
            return True

        if not state.is_open:
            return True

        if state.opened_at is None:
            return False

        elapsed = monotonic() - state.opened_at

        if elapsed >= self.cooldown_seconds:
            self.reset(model_key)
            return True

        return False

    def open(
        self,
        model_key: str,
    ) -> None:
        """Open the circuit for a model."""

        self._circuits[model_key] = CircuitState(
            is_open=True,
            opened_at=monotonic(),
        )

    def reset(
        self,
        model_key: str,
    ) -> None:
        """Reset the circuit for a model."""

        self._circuits.pop(
            model_key,
            None,
        )

    def status(
        self,
        model_key: str,
    ) -> str:
        """Return the current circuit status."""

        return (
            "open"
            if not self.is_available(model_key)
            else "closed"
        )

