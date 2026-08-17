"""
MinIO object storage implementation.
"""

from io import BytesIO

from minio import Minio

from app.config import settings
from app.storage.storage_service import StorageService


class MinIOStorageService(StorageService):
    """
    Object storage implementation using MinIO.
    """

    def __init__(
        self,
        client: Minio | None = None,
    ) -> None:
        """
        Initialize MinIO storage client.

        Args:
            client: Optional MinIO client for testing.
        """
        self._client = client or Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

        self._bucket_name = (
            settings.MINIO_BUCKET_NAME
        )

        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        """
        Ensure the configured bucket exists.
        """
        if not self._client.bucket_exists(
            self._bucket_name
        ):
            self._client.make_bucket(
                self._bucket_name
            )

    def save(
        self,
        file_content: bytes,
        object_key: str,
        content_type: str,
    ) -> str:
        """
        Store an object in MinIO.

        Args:
            file_content: Binary file content.
            object_key: Object key.
            content_type: MIME type.

        Returns:
            Stored object key.
        """
        self._client.put_object(
            self._bucket_name,
            object_key,
            BytesIO(file_content),
            length=len(file_content),
            content_type=content_type,
        )

        return object_key