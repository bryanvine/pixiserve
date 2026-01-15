from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator, BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    async def write(self, path: str, data: bytes | BinaryIO) -> str:
        """Write data to storage and return the final path."""
        pass

    @abstractmethod
    async def read(self, path: str) -> bytes:
        """Read data from storage."""
        pass

    @abstractmethod
    async def read_stream(self, path: str) -> AsyncIterator[bytes]:
        """Stream data from storage in chunks."""
        pass

    @abstractmethod
    async def delete(self, path: str) -> bool:
        """Delete a file from storage. Returns True if deleted."""
        pass

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if a file exists in storage."""
        pass

    @abstractmethod
    async def get_size(self, path: str) -> int:
        """Get the size of a file in bytes."""
        pass

    @abstractmethod
    def get_url(self, path: str) -> str:
        """Get a URL or path for accessing the file."""
        pass
