from bson import ObjectId

from app.core.database import get_database
from app.models.user import USERS_COLLECTION


async def get_user_by_id(user_id: str) -> dict | None:
    if not ObjectId.is_valid(user_id):
        return None
    return await get_database()[USERS_COLLECTION].find_one({"_id": ObjectId(user_id)})


def to_public_user(user: dict) -> dict:
    """The only safe way to send a user to the client. passwordHash is never included."""
    department_id = user.get("departmentId")
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "email": user["email"],
        "phone": user.get("phone"),
        "role": user["role"],
        "departmentId": str(department_id) if department_id else None,
        "points": user.get("points", 0),
        "badges": user.get("badges", []),
        "isActive": user["isActive"],
        "createdAt": user["createdAt"],
    }