from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import ApiError


def detect_image_extension(content: bytes) -> str | None:
    """Looks at the first bytes of the file ("magic bytes") to find the real type."""
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return ".webp"
    return None


async def read_and_validate_image(photo: UploadFile) -> tuple[bytes, str]:
    """Returns (file bytes, safe extension) or raises an error.

    We ignore the file name and the content-type header sent by the client,
    because both can be faked. Only the file's own bytes are trusted.
    """
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await photo.read(max_bytes + 1)  # read one extra byte to detect "too big"

    if not content:
        raise ApiError(400, "The uploaded photo is empty")
    if len(content) > max_bytes:
        raise ApiError(413, f"Photo is too large. Maximum size is {settings.max_upload_mb} MB")

    extension = detect_image_extension(content)
    if extension is None:
        raise ApiError(400, "Only JPEG, PNG or WebP images are allowed")
    return content, extension
