import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_model = os.getenv(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv(
            "GROQ_MODEL",
            "qwen/qwen3.6-27b",
        )

        self.database_url = os.getenv(
            "DATABASE_URL"
        )

        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set."
            )


settings = Settings()