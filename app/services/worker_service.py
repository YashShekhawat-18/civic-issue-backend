"""What a WORKER can see: only complaints of their own department."""
from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.category import CATEGORIES_COLLECTION
from app.models.complaint import ALLOWED_TRANSITIONS, COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.user import USERS_COLLECTION


def require_department_id(worker: dict):
    """The department comes from the worker's account in the database, never from the request."""
    department_id = worker.get("departmentId")
    if department_id is None:
        raise ApiError(403, "Your account is not assigned to a department")
    return department_id


def _summary(document: dict | None) -> dict | None:
    if document is None:
        return None
    return {"id": str(document["_id"]), "name": document["name"], "code": document["code"]}


async def to_worker_views(db, complaints: list[dict]) -> list[dict]:
    """Adds names with 3 queries in total (not 3 per complaint)."""
    if not complaints:
        return []

    category_cursor = db[CATEGORIES_COLLECTION].find({"_id": {"$in": list({c["categoryId"] for c in complaints})}})
    department_cursor = db[DEPARTMENTS_COLLECTION].find({"_id": {"$in": list({c["departmentId"] for c in complaints})}})
    people_ids = {c["reportedBy"] for c in complaints} | {
        c["assignedWorker"] for c in complaints if c.get("assignedWorker")
    }
    people_cursor = db[USERS_COLLECTION].find({"_id": {"$in": list(people_ids)}}, {"name": 1})

    categories = {c["_id"]: c for c in await category_cursor.to_list()}
    departments = {d["_id"]: d for d in await department_cursor.to_list()}
    people = {p["_id"]: p for p in await people_cursor.to_list()}

    views = []
    for complaint in complaints:
        assigned = people.get(complaint.get("assignedWorker"))
        reporter = people.get(complaint["reportedBy"])
        status = ComplaintStatus(complaint["status"])
        views.append(
            {
                "id": str(complaint["_id"]),
                "complaintNumber": complaint["complaintNumber"],
                "title": complaint["title"],
                "description": complaint["description"],
                "category": _summary(categories.get(complaint["categoryId"])),
                "department": _summary(departments.get(complaint["departmentId"])),
                "photoUrl": complaint["photoUrl"],
                "location": complaint["location"],
                "status": complaint["status"],
                "allowedNextStatuses": [s.value for s in ALLOWED_TRANSITIONS[status]],
                "priority": complaint["priority"],
                "upvoteCount": complaint["upvoteCount"],
                "overdue": complaint["overdue"],
                "isAnonymous": complaint["isAnonymous"],
                # Only the name, and nothing at all for anonymous complaints. No email or phone.
                "reporter": None if complaint["isAnonymous"] or reporter is None else {"name": reporter["name"]},
                "assignedWorker": {"id": str(assigned["_id"]), "name": assigned["name"]} if assigned else None,
                "resolvedAt": complaint["resolvedAt"],
                "createdAt": complaint["createdAt"],
                "updatedAt": complaint["updatedAt"],
            }
        )
    return views


async def list_department_complaints(
    *,
    worker: dict,
    status: ComplaintStatus | None,
    assigned_to_me: bool,
    overdue: bool | None,
    page: int,
    limit: int,
) -> dict:
    db = get_database()
    query: dict = {"departmentId": require_department_id(worker)}
    if status is not None:
        query["status"] = status.value
    if assigned_to_me:
        query["assignedWorker"] = worker["_id"]
    if overdue is not None:
        query["overdue"] = overdue

    complaints_collection = db[COMPLAINTS_COLLECTION]
    total = await complaints_collection.count_documents(query)
    cursor = complaints_collection.find(query).sort("createdAt", -1).skip((page - 1) * limit).limit(limit)
    complaints = await cursor.to_list()
    return {"items": await to_worker_views(db, complaints), "page": page, "limit": limit, "total": total}


async def get_department_complaint(*, worker: dict, complaint_id: str) -> dict:
    db = get_database()
    object_id = parse_object_id(complaint_id, "complaint id")
    complaint = await db[COMPLAINTS_COLLECTION].find_one(
        {"_id": object_id, "departmentId": require_department_id(worker)}
    )
    if complaint is None:
        # Same answer for "does not exist" and "belongs to another department"
        raise ApiError(404, "Complaint not found")
    return (await to_worker_views(db, [complaint]))[0]
