from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import ApiError
from app.services import geotag_service


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


def _format_distance(metres: float) -> str:
    return f"{round(metres)} m" if metres < 1000 else f"{metres / 1000:.1f} km"


def _photo_error(message: str) -> ApiError:
    return ApiError(422, "Validation failed", [{"field": "photo", "message": message}])


async def read_geotagged_image(
    photo: UploadFile, *, latitude: float, longitude: float, place: str
) -> tuple[bytes, str, tuple[float, float] | None]:
    """Like read_and_validate_image, and also checks WHERE the photo was taken.

    The photo must carry GPS data (JPEG) and must have been taken within
    GEOTAG_MAX_DISTANCE_METERS of (latitude, longitude). `place` is used in the message,
    for example "the pinned location" or "the reported location".
    Returns (bytes, extension, (photo latitude, photo longitude)).
    """
    content, extension = await read_and_validate_image(photo)
    if not settings.require_photo_gps:
        return content, extension, geotag_service.read_gps(content)

    position = geotag_service.read_gps(content)
    if position is None:
        raise _photo_error(
            "This photo has no GPS location. Turn on location for your camera and take the photo again "
            "(screenshots, downloaded pictures and PNG or WebP files have no location)."
        )
    metres = geotag_service.distance_meters(position[0], position[1], latitude, longitude)
    if metres > settings.geotag_max_distance_meters:
        raise _photo_error(
            f"This photo was taken {_format_distance(metres)} from {place}. It must be within "
            f"{settings.geotag_max_distance_meters} m. Take the photo at the spot."
        )
    return content, extension, position
