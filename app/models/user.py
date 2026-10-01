from datetime import datetime, timezone
from enum import Enum


class Role(str, Enum):
    CITIZEN = "CITIZEN"
    WORKER = "WORKER"
    ADMIN = "ADMIN"


USERS_COLLECTION = "users"


def build_user_document(
    *, name, email, password_hash, phone=None, role=Role.CITIZEN, department_id=None
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "name": name,
        "email": email,
        "passwordHash": password_hash,
        "phone": phone,
        "role": role.value,
        "departmentId": department_id,  # filled for workers from Phase 3
        "points": 0,
        "badges": [],
        "isActive": True,
        "createdAt": now,
        "updatedAt": now,
    }


async def create_user_indexes(db) -> None:
    # Unique index: MongoDB itself refuses two users with the same email
    await db[USERS_COLLECTION].create_index("email", unique=True)