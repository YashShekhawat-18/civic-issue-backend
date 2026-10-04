from functools import lru_cache

from app.core.config import settings
from app.storage.base import StorageBackend
from app.storage.local_storage import LocalStorage


@lru_cache
def get_storage() -> StorageBackend:
    # To switch to Cloudinary/S3 later, return a different StorageBackend here
    return LocalStorage(base_dir=settings.upload_dir, url_prefix="/uploads")
