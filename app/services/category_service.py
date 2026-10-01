from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.category import CATEGORIES_COLLECTION
from app.models.department import DEPARTMENTS_COLLECTION
from app.services.department_service import to_public_department


def to_public_category(category: dict, department: dict | None) -> dict:
    return {
        "id": str(category["_id"]),
        "name": category["name"],
        "code": category["code"],
        "description": category.get("description", ""),
        "isActive": category["isActive"],
        "department": to_public_department(department) if department else None,
    }


async def _find_departments_by_id(department_ids) -> dict:
    cursor = get_database()[DEPARTMENTS_COLLECTION].find({"_id": {"$in": list(department_ids)}})
    return {department["_id"]: department for department in await cursor.to_list()}


async def list_active_categories() -> list[dict]:
    cursor = get_database()[CATEGORIES_COLLECTION].find({"isActive": True}).sort("name", 1)
    categories = await cursor.to_list()
    departments = await _find_departments_by_id({c["departmentId"] for c in categories})
    return [to_public_category(c, departments.get(c["departmentId"])) for c in categories]


async def get_category_or_404(category_id: str) -> dict:
    """Returns the raw category document. Phase 4 uses this when a complaint is created."""
    object_id = parse_object_id(category_id, "category id")
    category = await get_database()[CATEGORIES_COLLECTION].find_one(
        {"_id": object_id, "isActive": True}
    )
    if category is None:
        raise ApiError(404, "Category not found")
    return category


async def get_category_details(category_id: str) -> dict:
    category = await get_category_or_404(category_id)
    departments = await _find_departments_by_id({category["departmentId"]})
    return to_public_category(category, departments.get(category["departmentId"]))