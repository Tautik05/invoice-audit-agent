from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract interface for structured LLM extraction providers."""

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        response_schema: Any,
    ) -> str:
        """Generate a structured response and return it as JSON text."""
        raise NotImplementedError