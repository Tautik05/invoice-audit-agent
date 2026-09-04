from app.llm.client import GeminiClient
from app.config import settings


def test_gemini_client_initializes():
    client = GeminiClient()

    assert client.client is not None
    assert client.model == settings.gemini_model