from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings


if not settings.database_url:
    raise ValueError(
        "DATABASE_URL is not set."
    )


database_url = settings.database_url

if database_url.startswith(
    "postgresql://"
):
    database_url = database_url.replace(
        "postgresql://",
        "postgresql+psycopg://",
        1,
    )

elif database_url.startswith(
    "postgres://"
):
    database_url = database_url.replace(
        "postgres://",
        "postgresql+psycopg://",
        1,
    )


engine = create_engine(
    database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)