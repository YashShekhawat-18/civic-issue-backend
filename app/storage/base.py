from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    async def save(self, content: bytes, extension: str, folder: str) -> str:
        """Store the file and return the URL/path to keep in the database."""

    @abstractmethod
    async def delete(self, url: str) -> None:
        """Remove a stored file (used to clean up if saving the complaint fails)."""
