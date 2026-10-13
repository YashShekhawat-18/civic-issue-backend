"""Admin's view of complaints: list, filter, map, detail, edit, delete."""
import logging
from datetime import datetime, timezone

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.category import CATEGORIES_COLLECTION
from app.models.audit_log import AuditAction
from app.models.complaint import COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.notification import NOTIFICATIONS_COLLECTION
from app.models.upvote import UPVOTES_COLLECTION
from app.models.user import USERS_COLLECTION, Role
from app.schemas.admin import ComplaintUpdate
from app.services import audit_service, worker_service
from app.storage import get_storage

logger = logging.getLogger("civic.admin")
MAP_DEFAULT_LIMIT = 500


async def to_admin_views(db, complaints: list[dict]) -> list[dict]:
    """Like the worker view, plus the reporter's id (but never for anonymous complaints)."""
    views = await worker_service.to_worker_views(db, complaints)
    for view, complaint in zip(views, complaints):
        if view["reporter"] is not None:
            view["reporter"] = {"id": str(complaint["reportedBy"]), **view["reporter"]}
    return views


def _build_filters(*, status, category_id, department_id, overdue, number) -> dict:
    query: dict = {}
    if status is not None:
        query["status"] = status.value
    if category_id is not None:
        query["categoryId"] = parse_object_id(category_id, "category id")
    if department_id is not None:
        query["departmentId"] = parse_object_id(department_id, "department id")
    if overdue is not None:
        query["overdue"] = overdue
    if number is not None:
        query["complaintNumber"] = number.strip().upper()
    return query


async def list_complaints(*, status, category_id, department_id, overdue, number, page: int, limit: int) -> dict:
    db = get_database()
    query = _build_filters(status=status, category_id=category_id, department_id=department_id, overdue=overdue, number=number)
    collection = db[COMPLAINTS_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("createdAt", -1).skip((page - 1) * limit).limit(limit)
    complaints = await cursor.to_list()
    return {"items": await to_admin_views(db, complaints), "page": page, "limit": limit, "total": total}


async def list_for_map(*, status, category_id, department_id, overdue, limit: int) -> dict:
    """Small records for drawing pins on a map: no description, no photo, no names of people."""
    db = get_database()
    query = _build_filters(status=status, category_id=category_id, department_id=department_id, overdue=overdue, number=None)
    cursor = db[COMPLAINTS_COLLECTION].find(
        query,
        {"complaintNumber": 1, "title": 1, "status": 1, "priority": 1, "overdue": 1, "location": 1,
         "categoryId": 1, "departmentId": 1, "upvoteCount": 1, "createdAt": 1},
    ).sort("createdAt", -1).limit(limit)
    complaints = await cursor.to_list()

    categories = {c["_id"]: c for c in await db[CATEGORIES_COLLECTION].find({"_id": {"$in": list({c["categoryId"] for c in complaints})}}).to_list()}
    departments = {d["_id"]: d for d in await db[DEPARTMENTS_COLLECTION].find({"_id": {"$in": list({c["departmentId"] for c in complaints})}}).to_list()}

    def brief(doc):
        return {"id": str(doc["_id"]), "name": doc["name"], "code": doc["code"]} if doc else None

    items = []
    for c in complaints:
        longitude, latitude = c["location"]["coordinates"]  # GeoJSON order is [longitude, latitude]
        items.append(
            {
                "id": str(c["_id"]),
                "complaintNumber": c["complaintNumber"],
                "title": c["title"],
                "status": c["status"],
                "priority": c["priority"],
                "overdue": c["overdue"],
                "upvoteCount": c["upvoteCount"],
                "category": brief(categories.get(c["categoryId"])),
                "department": brief(departments.get(c["departmentId"])),
                "latitude": latitude,
                "longitude": longitude,
                "createdAt": c["createdAt"],
            }
        )
    return {"items": items, "count": len(items), "limit": limit}


async def get_complaint(complaint_id: str) -> dict:
    db = get_database()
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": parse_object_id(complaint_id, "complaint id")})
    if complaint is None:
        raise ApiError(404, "Complaint not found")
    return (await to_admin_views(db, [complaint]))[0]


async def _active_worker_of(db, worker_id: str, department_id) -> dict:
    worker = await db[USERS_COLLECTION].find_one({"_id": parse_object_id(worker_id, "worker id"), "role": Role.WORKER.value})
    if worker is None or not worker["isActive"]:
        raise ApiError(404, "Worker not found")
    if worker.get("departmentId") != department_id:
        raise ApiError(409, "This worker belongs to a different department")
    return worker


async def update_complaint(*, actor: dict, complaint_id: str, data: ComplaintUpdate) -> dict:
    db = get_database()
    complaints = db[COMPLAINTS_COLLECTION]
    complaint = await complaints.find_one({"_id": parse_object_id(complaint_id, "complaint id")})
    if complaint is None:
        raise ApiError(404, "Complaint not found")

    changes: dict = {}      # what goes into MongoDB
    audit: dict = {}        # what goes into the audit log: {field: [old, new]}
    sent = data.model_fields_set

    for field in ("title", "description"):
        new_value = getattr(data, field)
        if field in sent and new_value is not None and new_value != complaint[field]:
            changes[field] = new_value
            audit[field] = [complaint[field], new_value]
    if "priority" in sent and data.priority is not None and data.priority.value != complaint["priority"]:
        changes["priority"] = data.priority.value
        audit["priority"] = [complaint["priority"], data.priority.value]

    department_id = complaint["departmentId"]
    if "category_id" in sent and data.category_id is not None:
        category = await db[CATEGORIES_COLLECTION].find_one({"_id": parse_object_id(data.category_id, "category id"), "isActive": True})
        if category is None:
            raise ApiError(404, "Category not found")
        if category["_id"] != complaint["categoryId"]:
            if complaint["status"] == ComplaintStatus.RESOLVED.value:
                raise ApiError(409, "The category of a resolved complaint cannot be changed")
            department = await db[DEPARTMENTS_COLLECTION].find_one({"_id": category["departmentId"], "isActive": True})
            if department is None:
                raise ApiError(409, "This category is not linked to an active department")
            # The department always follows the category (read from MongoDB, never from the request)
            changes["categoryId"] = category["_id"]
            changes["departmentId"] = department["_id"]
            audit["categoryId"] = [complaint["categoryId"], category["_id"]]
            if department["_id"] != complaint["departmentId"]:
                audit["departmentId"] = [complaint["departmentId"], department["_id"]]
                department_id = department["_id"]
                if complaint.get("assignedWorker") is not None and "assigned_worker_id" not in sent:
                    changes["assignedWorker"] = None  # the old worker is from another department
                    audit["assignedWorker"] = [complaint["assignedWorker"], None]

    if "assigned_worker_id" in sent:
        if data.assigned_worker_id is None:
            new_worker = None
        else:
            new_worker = (await _active_worker_of(db, data.assigned_worker_id, department_id))["_id"]
        if new_worker != complaint.get("assignedWorker"):
            changes["assignedWorker"] = new_worker
            audit["assignedWorker"] = [complaint.get("assignedWorker"), new_worker]

    if changes:
        changes["updatedAt"] = datetime.now(timezone.utc)
        await complaints.update_one({"_id": complaint["_id"]}, {"$set": changes})
        await audit_service.log_action(
            actor=actor,
            action=AuditAction.COMPLAINT_UPDATED,
            entity="COMPLAINT",
            entity_id=complaint["_id"],
            metadata={"complaintNumber": complaint["complaintNumber"], "changes": audit},
        )
    return await get_complaint(complaint_id)


async def delete_complaint(*, actor: dict, complaint_id: str) -> dict:
    db = get_database()
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": parse_object_id(complaint_id, "complaint id")})
    if complaint is None:
        raise ApiError(404, "Complaint not found")

    # Remove the complaint and everything that only makes sense together with it
    await db[COMPLAINTS_COLLECTION].delete_one({"_id": complaint["_id"]})
    await db[UPVOTES_COLLECTION].delete_many({"complaintId": complaint["_id"]})
    await db[NOTIFICATIONS_COLLECTION].delete_many({"complaintId": complaint["_id"]})
    try:
        await get_storage().delete(complaint["photoUrl"])
    except Exception:
        logger.exception("Could not delete the photo of %s", complaint["complaintNumber"])

    await audit_service.log_action(
        actor=actor,
        action=AuditAction.COMPLAINT_DELETED,
        entity="COMPLAINT",
        entity_id=complaint["_id"],
        metadata={
            "complaintNumber": complaint["complaintNumber"],
            "title": complaint["title"],
            "status": complaint["status"],
            "upvoteCount": complaint["upvoteCount"],
        },
    )
    return {"id": str(complaint["_id"]), "complaintNumber": complaint["complaintNumber"], "deleted": True}
