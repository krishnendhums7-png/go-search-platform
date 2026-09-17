"""Initialize the Kerala Government Orders PostgreSQL database."""

from app.storage.relational.database import create_database_engine
from app.storage.relational.models import Base


def main() -> None:
    """Create the PostgreSQL database tables."""
    engine = create_database_engine()

    Base.metadata.create_all(engine)

    print("PostgreSQL tables initialized successfully.")


if __name__ == "__main__":
    main()