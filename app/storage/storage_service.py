"""
Object storage abstraction.
"""

from abc import ABC
from abc import abstractmethod


class StorageService(ABC):
    """
    Abstract interface for object storage.

    Implementations can use mock storage or MinIO.
    """

    @abstractmethod
    def save(
        self,
        file_content: bytes,
        object_key: str,
        content_type: str,
    ) -> str:
        """
        Store an object.

        Args:
            file_content: Binary content.
            object_key: Destination object key.
            content_type: MIME type.

        Returns:
            Stored object key.
        """
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        object_key: str,
    ) -> bytes:
        """
        Retrieve an object.

        Args:
            object_key: Object storage key.

        Returns:
            Object bytes.
        """
        raise NotImplementedError