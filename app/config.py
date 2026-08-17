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

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()