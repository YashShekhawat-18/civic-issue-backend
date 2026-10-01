from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.department import DEPARTMENTS_COLLECTION


def to_public_department(department: dict) -> dict:
    return {
        "id": str(department["_id"]),
        "name": department["name"],
        "code": department["code"],
        "description": department.get("description", ""),
        "isActive": department["isActive"],
    }


async def list_active_departments() -> list[dict]:
    cursor = get_database()[DEPARTMENTS_COLLECTION].find({"isActive": True}).sort("name", 1)
    return [to_public_department(department) for department in await cursor.to_list()]


async def get_department_or_404(department_id: str) -> dict:
    object_id = parse_object_id(department_id, "department id")
    department = await get_database()[DEPARTMENTS_COLLECTION].find_one(
        {"_id": object_id, "isActive": True}
    )
    if department is None:
        raise ApiError(404, "Department not found")
    return department