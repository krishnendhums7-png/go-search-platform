"""SQLAlchemy session management."""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.storage.relational.database import create_database_engine


engine = create_database_engine()

SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_session() -> Generator[Session, None, None]:
    """Create and yield a database session.

    Yields:
        SQLAlchemy database session.
    """
    session = SessionFactory()

    try:
        yield session
    finally:
        session.close()