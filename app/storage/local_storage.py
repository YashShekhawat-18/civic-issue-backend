import asyncio
import uuid
from pathlib import Path

from app.storage.base import StorageBackend


class LocalStorage(StorageBackend):
    """Saves files on this computer's disk, inside the upload folder."""

    def __init__(self, base_dir: str, url_prefix: str = "/uploads"):
        self.base_dir = Path(base_dir).resolve()
        self.url_prefix = url_prefix.rstrip("/")

    async def save(self, content: bytes, extension: str, folder: str) -> str:
        # The file name is random. The name the user uploaded is never used.
        filename = f"{uuid.uuid4().hex}{extension}"
        target_dir = self.base_dir / folder

        def write_file() -> None:
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / filename).write_bytes(content)

        await asyncio.to_thread(write_file)
        return f"{self.url_prefix}/{folder}/{filename}"

    async def delete(self, url: str) -> None:
        relative_path = url.removeprefix(self.url_prefix + "/")
        file_path = (self.base_dir / relative_path).resolve()
        if self.base_dir not in file_path.parents:
            return  # never delete anything outside the upload folder
        await asyncio.to_thread(lambda: file_path.unlink(missing_ok=True))
