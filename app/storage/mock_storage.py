"""
In-memory object storage used for development and unit testing.
"""

from app.storage.storage_service import StorageService


class MockStorageService(StorageService):
    """
    Temporary object-storage implementation.

    This class allows Module 2 to be developed and tested
    without requiring a running MinIO server.
    """

    def __init__(self) -> None:
        """
        Initialize empty mock storage.
        """
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
            file_content: Binary file content.
            object_key: Object storage key.
            content_type: MIME type.

        Returns:
            Stored object key.
        """
        self._objects[object_key] = file_content

        return object_key

    def get(
        self,
        object_key: str,
    ) -> bytes | None:
        """
        Retrieve an object from mock storage.

        Args:
            object_key: Object storage key.

        Returns:
            Stored bytes or None.
        """
        return self._objects.get(object_key)