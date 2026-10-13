"""Admin management of WORKER accounts. The role is always WORKER here, never taken from a request."""
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.core.security import hash_password
from app.models.audit_log import AuditAction
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.user import USERS_COLLECTION, Role, build_user_document
from app.schemas.admin import WorkerCreate, WorkerUpdate
from app.services import audit_service
from app.services.user_service import to_public_user

EMAIL_TAKEN = "An account with this email already exists"


async def _active_department(db, department_id: str) -> dict:
    department = await db[DEPARTMENTS_COLLECTION].find_one({"_id": parse_object_id(department_id, "department id"), "isActive": True})
    if department is None:
        raise ApiError(404, "Department not found")
    return department


async def _get_worker(db, worker_id: str) -> dict:
    worker = await db[USERS_COLLECTION].find_one({"_id": parse_object_id(worker_id, "worker id"), "role": Role.WORKER.value})
    if worker is None:
        raise ApiError(404, "Worker not found")
    return worker


async def _with_department(db, workers: list[dict]) -> list[dict]:
    department_ids = list({w["departmentId"] for w in workers if w.get("departmentId")})
    departments = {d["_id"]: d for d in await db[DEPARTMENTS_COLLECTION].find({"_id": {"$in": department_ids}}).to_list()} if department_ids else {}
    items = []
    for worker in workers:
        item = to_public_user(worker)
        department = departments.get(worker.get("departmentId"))
        item["department"] = {"id": str(department["_id"]), "name": department["name"], "code": department["code"]} if department else None
        items.append(item)
    return items


async def create_worker(*, actor: dict, data: WorkerCreate) -> dict:
    db = get_database()
    department = await _active_department(db, data.department_id)
    if await db[USERS_COLLECTION].find_one({"email": data.email}, {"_id": 1}):
        raise ApiError(409, EMAIL_TAKEN)

    document = build_user_document(
        name=data.name, email=data.email, password_hash=await hash_password(data.password),
        phone=data.phone, role=Role.WORKER, department_id=department["_id"],
    )
    try:
        await db[USERS_COLLECTION].insert_one(document)
    except DuplicateKeyError:
        raise ApiError(409, EMAIL_TAKEN)

    await audit_service.log_action(
        actor=actor, action=AuditAction.WORKER_CREATED, entity="USER", entity_id=document["_id"],
        metadata={"name": document["name"], "departmentCode": department["code"]},
    )
    return (await _with_department(db, [document]))[0]


async def list_workers(*, department_id: str | None, is_active: bool | None, page: int, limit: int) -> dict:
    db = get_database()
    query: dict = {"role": Role.WORKER.value}
    if department_id is not None:
        query["departmentId"] = parse_object_id(department_id, "department id")
    if is_active is not None:
        query["isActive"] = is_active
    users = db[USERS_COLLECTION]
    total = await users.count_documents(query)
    workers = await users.find(query).sort("name", 1).skip((page - 1) * limit).limit(limit).to_list()
    return {"items": await _with_department(db, workers), "page": page, "limit": limit, "total": total}


async def get_worker(worker_id: str) -> dict:
    db = get_database()
    return (await _with_department(db, [await _get_worker(db, worker_id)]))[0]


async def update_worker(*, actor: dict, worker_id: str, data: WorkerUpdate) -> dict:
    db = get_database()
    worker = await _get_worker(db, worker_id)
    sent = data.model_fields_set

    updates: dict = {}
    if "name" in sent and data.name is not None:
        updates["name"] = data.name
    if "phone" in sent:
        updates["phone"] = data.phone  # null removes the phone number
    if "department_id" in sent and data.department_id is not None:
        updates["departmentId"] = (await _active_department(db, data.department_id))["_id"]
    if "is_active" in sent and data.is_active is not None:
        updates["isActive"] = data.is_active
    password_reset = "password" in sent and data.password is not None
    if password_reset:
        updates["passwordHash"] = await hash_password(data.password)

    if updates:
        updates["updatedAt"] = datetime.now(timezone.utc)
        worker = await db[USERS_COLLECTION].find_one_and_update(
            {"_id": worker["_id"]}, {"$set": updates}, return_document=ReturnDocument.AFTER
        )
        safe_changes = sorted(k for k in updates if k not in ("passwordHash", "updatedAt"))
        deactivated = updates.get("isActive") is False
        await audit_service.log_action(
            actor=actor,
            action=AuditAction.WORKER_DEACTIVATED if deactivated else AuditAction.WORKER_UPDATED,
            entity="USER", entity_id=worker["_id"],
            metadata={"fields": safe_changes, "passwordReset": password_reset},
        )
    return (await _with_department(db, [worker]))[0]


async def deactivate_worker(*, actor: dict, worker_id: str) -> dict:
    return await update_worker(actor=actor, worker_id=worker_id, data=WorkerUpdate(isActive=False))
