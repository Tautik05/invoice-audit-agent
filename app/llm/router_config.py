from app.config import settings
from app.llm.router import LLMRouter, ModelConfig


def create_llm_router() -> LLMRouter:

    models = [
        ModelConfig(
            provider="gemini",
            model=settings.gemini_model,
        ),
        ModelConfig(
            provider="gemini",
            model="gemini-3.7-flash",
        ),
    ]

    if settings.groq_api_key:
        models.extend(
            [
                ModelConfig(
                    provider="groq",
                    model="qwen/qwen3.6-27b",
                ),
                ModelConfig(
                    provider="groq",
                    model="openai/gpt-oss-120b",
                ),
                ModelConfig(
                    provider="groq",
                    model="llama-3.3-70b-versatile",
                ),
            ]
        )

    return LLMRouter(models)