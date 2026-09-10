from collections.abc import Iterator

from langgraph.checkpoint.postgres import PostgresSaver

from app.config import settings


def postgres_checkpointer() -> Iterator[PostgresSaver]:
    """Create a PostgreSQL-backed LangGraph checkpointer."""

    if not settings.database_url:
        raise ValueError("DATABASE_URL is not set.")

    database_url = settings.database_url

    if database_url.startswith("postgresql+psycopg://"):
        database_url = database_url.replace(
            "postgresql+psycopg://",
            "postgresql://",
            1,
        )
    elif database_url.startswith("postgres+psycopg://"):
        database_url = database_url.replace(
            "postgres+psycopg://",
            "postgresql://",
            1,
        )

    return PostgresSaver.from_conn_string(
        database_url
    )