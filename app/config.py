"""
Application configuration.
"""

from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    """

    APP_NAME: str

    APP_VERSION: str

    APP_ENV: str

    LOG_LEVEL: str

    JWT_SECRET_KEY: str

    JWT_ALGORITHM: str

    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    MINIO_ENDPOINT: str

    MINIO_ACCESS_KEY: str

    MINIO_SECRET_KEY: str

    MINIO_BUCKET_NAME: str

    MINIO_SECURE: bool = False

    POSTGRES_USER: str = "go_user"

    POSTGRES_PASSWORD: str = "go_password"

    POSTGRES_HOST: str = "localhost"

    POSTGRES_PORT: int = 5432

    POSTGRES_DB: str = "kerala_go"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "government_orders"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()