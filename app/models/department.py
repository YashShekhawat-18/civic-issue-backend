from datetime import datetime, timezone

DEPARTMENTS_COLLECTION = "departments"


def build_department_document(*, name: str, code: str, description: str = "") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "code": code,
        "description": description,
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }


async def create_department_indexes(db) -> None:
    await db[DEPARTMENTS_COLLECTION].create_index("code", unique=True)
    await db[DEPARTMENTS_COLLECTION].create_index("name", unique=True)