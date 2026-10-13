from datetime import datetime, timezone
from enum import Enum


class AuditAction(str, Enum):
    STATUS_CHANGED = "STATUS_CHANGED"
    COMPLAINT_UPDATED = "COMPLAINT_UPDATED"
    COMPLAINT_DELETED = "COMPLAINT_DELETED"
    DEPARTMENT_CREATED = "DEPARTMENT_CREATED"
    DEPARTMENT_UPDATED = "DEPARTMENT_UPDATED"
    DEPARTMENT_DEACTIVATED = "DEPARTMENT_DEACTIVATED"
    CATEGORY_CREATED = "CATEGORY_CREATED"
    CATEGORY_UPDATED = "CATEGORY_UPDATED"
    CATEGORY_DEACTIVATED = "CATEGORY_DEACTIVATED"
    WORKER_CREATED = "WORKER_CREATED"
    WORKER_UPDATED = "WORKER_UPDATED"
    WORKER_DEACTIVATED = "WORKER_DEACTIVATED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PROFILE_UPDATED = "PROFILE_UPDATED"


AUDIT_LOGS_COLLECTION = "audit_logs"


def build_audit_document(*, user_id, action: AuditAction, entity: str, entity_id, metadata: dict) -> dict:
    return {
        "userId": user_id,       # who did it
        "action": action.value,  # what they did
        "entity": entity,        # what kind of thing: COMPLAINT, DEPARTMENT, CATEGORY, USER
        "entityId": entity_id,   # which one
        "metadata": metadata,    # small details (never passwords, tokens or emails)
        "createdAt": datetime.now(timezone.utc),
    }


async def create_audit_log_indexes(db) -> None:
    logs = db[AUDIT_LOGS_COLLECTION]
    await logs.create_index([("createdAt", -1)])
    await logs.create_index([("action", 1), ("createdAt", -1)])
    await logs.create_index([("userId", 1), ("createdAt", -1)])
    await logs.create_index([("entity", 1), ("entityId", 1)])
