"""
Object storage abstraction.
"""

from abc import ABC
from abc import abstractmethod


class StorageService(ABC):
    """
    Abstract interface for object storage.
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
            file_content: Binary file content.
            object_key: Destination object key.
            content_type: MIME type.

        Returns:
            Stored object key.
        """
        raise NotImplementedError