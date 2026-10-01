from bson import ObjectId

from app.core.errors import ApiError


def parse_object_id(value: str, name: str = "id") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise ApiError(400, f"Invalid {name}")
    return ObjectId(value)