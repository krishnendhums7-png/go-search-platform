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
        Initialize MinIO client.

        Args:
            client: Optional client for testing.
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
        """Create bucket if it does not exist."""
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
        """
        self._client.put_object(
            self._bucket_name,
            object_key,
            BytesIO(file_content),
            length=len(file_content),
            content_type=content_type,
        )

        return object_key

    def get(
        self,
        object_key: str,
    ) -> bytes:
        """
        Retrieve an object from MinIO.

        Args:
            object_key: Object storage key.

        Returns:
            Object bytes.
        """
        response = self._client.get_object(
            self._bucket_name,
            object_key,
        )

        try:
            return response.read()

        finally:
            response.close()
            response.release_conn()