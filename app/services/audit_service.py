"""Audit log: who did what, and when. Only important changes are recorded.

log_action() NEVER raises: a problem with the log must not stop the real action.
Never put passwords, tokens or e-mail addresses in `metadata`.
"""
import logging
from datetime import datetime

from bson import ObjectId

from app.core.database import get_database
from app.core.object_id import parse_object_id
from app.models.audit_log import AUDIT_LOGS_COLLECTION, AuditAction, build_audit_document
from app.models.user import USERS_COLLECTION

logger = logging.getLogger("civic.audit")


def _clean(value):
    """Makes metadata safe to store: ids become strings, and nesting is handled."""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, (str, int, float, bool, datetime)) or value is None:
        return value
    return str(value)


async def log_action(*, actor: dict | None, action: AuditAction, entity: str, entity_id, metadata: dict | None = None, db=None) -> None:
    try:
        if db is None:
            db = get_database()
        document = build_audit_document(
            user_id=actor["_id"] if actor else None,
            action=action,
            entity=entity,
            entity_id=entity_id,
            metadata=_clean(metadata or {}),
        )
        await db[AUDIT_LOGS_COLLECTION].insert_one(document)
    except Exception:
        logger.exception("Could not write the audit log for %s", action.value)


async def list_audit_logs(
    *, action: AuditAction | None, entity: str | None, user_id: str | None, page: int, limit: int
) -> dict:
    db = get_database()
    query: dict = {}
    if action is not None:
        query["action"] = action.value
    if entity is not None:
        query["entity"] = entity.upper()
    if user_id is not None:
        query["userId"] = parse_object_id(user_id, "user id")

    logs = db[AUDIT_LOGS_COLLECTION]
    total = await logs.count_documents(query)
    cursor = logs.find(query).sort("createdAt", -1).skip((page - 1) * limit).limit(limit)
    entries = await cursor.to_list()

    user_ids = list({e["userId"] for e in entries if e.get("userId")})
    users = {}
    if user_ids:
        users = {u["_id"]: u for u in await db[USERS_COLLECTION].find({"_id": {"$in": user_ids}}, {"name": 1, "role": 1}).to_list()}

    items = []
    for entry in entries:
        actor = users.get(entry.get("userId"))
        items.append(
            {
                "id": str(entry["_id"]),
                "action": entry["action"],
                "entity": entry["entity"],
                "entityId": str(entry["entityId"]) if entry.get("entityId") else None,
                "user": {"id": str(actor["_id"]), "name": actor["name"], "role": actor["role"]} if actor else None,
                "metadata": entry.get("metadata", {}),
                "createdAt": entry["createdAt"],
            }
        )
    return {"items": items, "page": page, "limit": limit, "total": total}
