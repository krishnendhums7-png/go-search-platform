"""PostgreSQL database configuration and initialization."""

from sqlalchemy import URL, create_engine
from sqlalchemy.engine import Engine

from app.config import settings


def create_database_engine() -> Engine:
    """Create the PostgreSQL database engine.

    Returns:
        SQLAlchemy engine connected to PostgreSQL.
    """
    database_url = URL.create(
        drivername="postgresql+psycopg",
        username=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database=settings.POSTGRES_DB,
    )

    return create_engine(
        database_url,
        pool_pre_ping=True,
    )