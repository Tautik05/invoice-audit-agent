from enum import Enum


class LLMErrorType(str, Enum):
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    QUOTA_EXHAUSTED = "quota_exhausted"
    AUTHENTICATION = "authentication"
    INVALID_REQUEST = "invalid_request"
    MODEL_NOT_FOUND = "model_not_found"
    UNKNOWN = "unknown"


class LLMError(Exception):
    """Normalized error raised by an LLM provider."""

    def __init__(
        self,
        message: str,
        error_type: LLMErrorType,
        provider: str,
        model: str,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)

        self.message = message
        self.error_type = error_type
        self.provider = provider
        self.model = model
        self.retryable = retryable