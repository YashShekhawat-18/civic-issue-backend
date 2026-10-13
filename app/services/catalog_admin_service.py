"""Admin management of departments and categories.

"Delete" never removes a document. It only sets isActive = false, so old complaints keep
pointing at a department and category that still exist.
"""
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.audit_log import AuditAction
from app.models.category import CATEGORIES_COLLECTION, build_category_document
from app.models.complaint import ACTIVE_STATUSES, COMPLAINTS_COLLECTION
from app.models.department import DEPARTMENTS_COLLECTION, build_department_document
from app.models.user import USERS_COLLECTION, Role
from app.schemas.admin import CategoryCreate, CategoryUpdate, DepartmentCreate, DepartmentUpdate
from app.services import audit_service
from app.services.category_service import to_public_category
from app.services.department_service import to_public_department

DUPLICATE_MESSAGE = "A {what} with this name or code already exists"


def _changed_fields(document: dict, updates: dict) -> dict:
    return {key: [document.get(key), value] for key, value in updates.items() if document.get(key) != value}


# ---------------------------------------------------------------- departments

async def _get_department(db, department_id: str, *, include_inactive: bool) -> dict:
    query = {"_id": parse_object_id(department_id, "department id")}
    if not include_inactive:
        query["isActive"] = True
    department = await db[DEPARTMENTS_COLLECTION].find_one(query)
    if department is None:
        raise ApiError(404, "Department not found")
    return department


async def get_department(department_id: str, viewer: dict) -> dict:
    db = get_database()
    department = await _get_department(db, department_id, include_inactive=viewer["role"] == Role.ADMIN.value)
    return to_public_department(department)


async def list_all_departments() -> list[dict]:
    cursor = get_database()[DEPARTMENTS_COLLECTION].find({}).sort("name", 1)
    return [to_public_department(d) for d in await cursor.to_list()]


async def create_department(*, actor: dict, data: DepartmentCreate) -> dict:
    db = get_database()
    document = build_department_document(name=data.name, code=data.code, description=data.description)
    try:
        await db[DEPARTMENTS_COLLECTION].insert_one(document)
    except DuplicateKeyError:
        raise ApiError(409, DUPLICATE_MESSAGE.format(what="department"))
    await audit_service.log_action(
        actor=actor, action=AuditAction.DEPARTMENT_CREATED, entity="DEPARTMENT", entity_id=document["_id"],
        metadata={"name": document["name"], "code": document["code"]},
    )
    return to_public_department(document)


async def _check_department_can_be_deactivated(db, department_id) -> None:
    if await db[CATEGORIES_COLLECTION].count_documents({"departmentId": department_id, "isActive": True}):
        raise ApiError(409, "This department still has active categories. Move or deactivate them first")
    if await db[USERS_COLLECTION].count_documents({"role": Role.WORKER.value, "departmentId": department_id, "isActive": True}):
        raise ApiError(409, "This department still has active workers. Move or deactivate them first")
    if await db[COMPLAINTS_COLLECTION].count_documents({"departmentId": department_id, "status": {"$in": ACTIVE_STATUSES}}):
        raise ApiError(409, "This department still has open complaints. Resolve or move them first")


async def update_department(*, actor: dict, department_id: str, data: DepartmentUpdate) -> dict:
    db = get_database()
    department = await _get_department(db, department_id, include_inactive=True)

    updates = {}
    for field in ("name", "code", "description"):
        if field in data.model_fields_set and getattr(data, field) is not None:
            updates[field] = getattr(data, field)
    if "is_active" in data.model_fields_set and data.is_active is not None:
        updates["isActive"] = data.is_active
        if data.is_active is False and department["isActive"]:
            await _check_department_can_be_deactivated(db, department["_id"])

    changes = _changed_fields(department, updates)
    if not changes:
        return to_public_department(department)

    updates["updatedAt"] = datetime.now(timezone.utc)
    try:
        updated = await db[DEPARTMENTS_COLLECTION].find_one_and_update(
            {"_id": department["_id"]}, {"$set": updates}, return_document=ReturnDocument.AFTER
        )
    except DuplicateKeyError:
        raise ApiError(409, DUPLICATE_MESSAGE.format(what="department"))

    deactivated = changes.get("isActive", [None, None])[1] is False
    await audit_service.log_action(
        actor=actor,
        action=AuditAction.DEPARTMENT_DEACTIVATED if deactivated else AuditAction.DEPARTMENT_UPDATED,
        entity="DEPARTMENT", entity_id=department["_id"],
        metadata={"code": department["code"], "changes": changes},
    )
    return to_public_department(updated)


async def deactivate_department(*, actor: dict, department_id: str) -> dict:
    return await update_department(actor=actor, department_id=department_id, data=DepartmentUpdate(isActive=False))


# ----------------------------------------------------------------- categories

async def _get_category(db, category_id: str, *, include_inactive: bool) -> dict:
    query = {"_id": parse_object_id(category_id, "category id")}
    if not include_inactive:
        query["isActive"] = True
    category = await db[CATEGORIES_COLLECTION].find_one(query)
    if category is None:
        raise ApiError(404, "Category not found")
    return category


async def _public_category(db, category: dict) -> dict:
    department = await db[DEPARTMENTS_COLLECTION].find_one({"_id": category["departmentId"]})
    return to_public_category(category, department)


async def get_category(category_id: str, viewer: dict) -> dict:
    db = get_database()
    category = await _get_category(db, category_id, include_inactive=viewer["role"] == Role.ADMIN.value)
    return await _public_category(db, category)


async def list_all_categories() -> list[dict]:
    db = get_database()
    categories = await db[CATEGORIES_COLLECTION].find({}).sort("name", 1).to_list()
    departments = {d["_id"]: d for d in await db[DEPARTMENTS_COLLECTION].find({"_id": {"$in": list({c["departmentId"] for c in categories})}}).to_list()}
    return [to_public_category(c, departments.get(c["departmentId"])) for c in categories]


async def _active_department(db, department_id: str) -> dict:
    department = await db[DEPARTMENTS_COLLECTION].find_one({"_id": parse_object_id(department_id, "department id"), "isActive": True})
    if department is None:
        raise ApiError(404, "Department not found")
    return department


async def create_category(*, actor: dict, data: CategoryCreate) -> dict:
    db = get_database()
    department = await _active_department(db, data.department_id)
    document = build_category_document(name=data.name, code=data.code, description=data.description, department_id=department["_id"])
    try:
        await db[CATEGORIES_COLLECTION].insert_one(document)
    except DuplicateKeyError:
        raise ApiError(409, DUPLICATE_MESSAGE.format(what="category"))
    await audit_service.log_action(
        actor=actor, action=AuditAction.CATEGORY_CREATED, entity="CATEGORY", entity_id=document["_id"],
        metadata={"name": document["name"], "code": document["code"], "departmentCode": department["code"]},
    )
    return to_public_category(document, department)


async def update_category(*, actor: dict, category_id: str, data: CategoryUpdate) -> dict:
    db = get_database()
    category = await _get_category(db, category_id, include_inactive=True)

    updates = {}
    for field in ("name", "code", "description"):
        if field in data.model_fields_set and getattr(data, field) is not None:
            updates[field] = getattr(data, field)
    target_department_id = category["departmentId"]
    if "department_id" in data.model_fields_set and data.department_id is not None:
        target_department_id = (await _active_department(db, data.department_id))["_id"]
        updates["departmentId"] = target_department_id  # only NEW complaints use the new department
    if "is_active" in data.model_fields_set and data.is_active is not None:
        updates["isActive"] = data.is_active
    if updates.get("isActive") is True:
        # a category can only be switched back on if its department is active
        await _active_department(db, str(target_department_id))

    changes = _changed_fields(category, updates)
    if not changes:
        return await _public_category(db, category)

    updates["updatedAt"] = datetime.now(timezone.utc)
    try:
        updated = await db[CATEGORIES_COLLECTION].find_one_and_update(
            {"_id": category["_id"]}, {"$set": updates}, return_document=ReturnDocument.AFTER
        )
    except DuplicateKeyError:
        raise ApiError(409, DUPLICATE_MESSAGE.format(what="category"))

    deactivated = changes.get("isActive", [None, None])[1] is False
    await audit_service.log_action(
        actor=actor,
        action=AuditAction.CATEGORY_DEACTIVATED if deactivated else AuditAction.CATEGORY_UPDATED,
        entity="CATEGORY", entity_id=category["_id"],
        metadata={"code": category["code"], "changes": changes},
    )
    return await _public_category(db, updated)


async def deactivate_category(*, actor: dict, category_id: str) -> dict:
    return await update_category(actor=actor, category_id=category_id, data=CategoryUpdate(isActive=False))
