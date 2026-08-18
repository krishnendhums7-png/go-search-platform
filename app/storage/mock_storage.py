"""
In-memory object storage used for development and testing.
"""

from app.storage.storage_service import StorageService


class MockStorageService(StorageService):
    """
    Temporary object-storage implementation.

    Used while MinIO is not available locally.
    """

    def __init__(self) -> None:
        """Initialize empty storage."""
        self._objects: dict[str, bytes] = {}

    def save(
        self,
        file_content: bytes,
        object_key: str,
        content_type: str,
    ) -> str:
        """
        Store an object in memory.

        Args:
            file_content: Binary content.
            object_key: Storage key.
            content_type: MIME type.

        Returns:
            Stored object key.
        """
        self._objects[object_key] = file_content

        return object_key

    def get(
        self,
        object_key: str,
    ) -> bytes:
        """
        Retrieve an object.

        Args:
            object_key: Storage key.

        Returns:
            Stored bytes.

        Raises:
            KeyError: If object does not exist.
        """
        if object_key not in self._objects:
            raise KeyError(
                f"Object not found: {object_key}"
            )

        return self._objects[object_key]