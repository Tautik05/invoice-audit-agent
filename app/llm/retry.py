import time
from collections.abc import Callable
from typing import TypeVar

from app.llm.errors import LLMError, LLMErrorType


T = TypeVar("T")


class RetryPolicy:
    """Controls retries for transient LLM failures."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 2.0,
        max_delay: float = 30.0,
    ) -> None:
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay

    def execute(
        self,
        operation: Callable[[], T],
    ) -> T:

        attempt = 0
        delay = self.initial_delay

        while True:
            attempt += 1

            try:
                return operation()

            except LLMError as exc:

                if not exc.retryable:
                    raise

                if attempt >= self.max_attempts:
                    raise

                time.sleep(delay)

                delay = min(
                    delay * 2,
                    self.max_delay,
                )