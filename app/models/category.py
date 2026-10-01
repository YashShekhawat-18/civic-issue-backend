from datetime import datetime, timezone

CATEGORIES_COLLECTION = "categories"


def build_category_document(*, name: str, code: str, description: str, department_id) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "code": code,
        "description": description,
        "departmentId": department_id,  # the link that decides which department gets a complaint
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }


async def create_category_indexes(db) -> None:
    await db[CATEGORIES_COLLECTION].create_index("code", unique=True)
    await db[CATEGORIES_COLLECTION].create_index("departmentId")