from datetime import datetime, timezone

from fastapi import UploadFile

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.category import CATEGORIES_COLLECTION
from app.models.complaint import COMPLAINTS_COLLECTION, ComplaintStatus, build_complaint_document
from app.models.counter import next_sequence
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.user import Role
from app.services import category_service, image_service
from app.storage import get_storage

PHOTO_FOLDER = "complaints"


def _clean_text(value: str, field: str, min_length: int) -> str:
    cleaned = value.strip()
    if len(cleaned) < min_length:
        message = f"{field.capitalize()} must be at least {min_length} characters"
        raise ApiError(422, "Validation failed", [{"field": field, "message": message}])
    return cleaned


async def generate_complaint_number(db) -> str:
    """Example: CIV-2026-000001. The counter restarts at 1 every year."""
    year = datetime.now(timezone.utc).year
    sequence = await next_sequence(db, f"complaint-{year}")
    return f"CIV-{year}-{sequence:06d}"


def _summary(document: dict | None) -> dict | None:
    if document is None:
        return None
    return {"id": str(document["_id"]), "name": document["name"], "code": document["code"]}


def to_public_complaint(complaint: dict, category: dict | None, department: dict | None) -> dict:
    return {
        "id": str(complaint["_id"]),
        "complaintNumber": complaint["complaintNumber"],
        "title": complaint["title"],
        "description": complaint["description"],
        "category": _summary(category),
        "department": _summary(department),
        "photoUrl": complaint["photoUrl"],
        "location": complaint["location"],
        "status": complaint["status"],
        "priority": complaint["priority"],
        "isAnonymous": complaint["isAnonymous"],
        "upvoteCount": complaint["upvoteCount"],
        "overdue": complaint["overdue"],
        "resolvedAt": complaint["resolvedAt"],
        "reportedBy": str(complaint["reportedBy"]),
        "createdAt": complaint["createdAt"],
        "updatedAt": complaint["updatedAt"],
    }


async def _to_public_list(db, complaints: list[dict]) -> list[dict]:
    """Adds the category and department names with 2 queries instead of 1 per complaint."""
    if not complaints:
        return []
    category_ids = list({c["categoryId"] for c in complaints})
    department_ids = list({c["departmentId"] for c in complaints})

    category_cursor = db[CATEGORIES_COLLECTION].find({"_id": {"$in": category_ids}})
    department_cursor = db[DEPARTMENTS_COLLECTION].find({"_id": {"$in": department_ids}})
    categories = {c["_id"]: c for c in await category_cursor.to_list()}
    departments = {d["_id"]: d for d in await department_cursor.to_list()}

    return [
        to_public_complaint(c, categories.get(c["categoryId"]), departments.get(c["departmentId"]))
        for c in complaints
    ]


async def create_complaint(
    *,
    reporter: dict,
    title: str,
    description: str,
    category_id: str,
    latitude: float,
    longitude: float,
    is_anonymous: bool,
    photo: UploadFile,
) -> dict:
    db = get_database()
    title = _clean_text(title, "title", 5)
    description = _clean_text(description, "description", 10)

    # The department is NEVER taken from the request. It comes from the category in MongoDB.
    category = await category_service.get_category_or_404(category_id)
    department = await db[DEPARTMENTS_COLLECTION].find_one(
        {"_id": category["departmentId"], "isActive": True}
    )
    if department is None:
        raise ApiError(409, "This category is not linked to an active department")

    content, extension = await image_service.read_and_validate_image(photo)

    # Phase 5 adds the "nearby duplicate" check here, before anything is saved.

    storage = get_storage()
    photo_url = await storage.save(content, extension, PHOTO_FOLDER)
    try:
        document = build_complaint_document(
            complaint_number=await generate_complaint_number(db),
            title=title,
            description=description,
            category_id=category["_id"],
            department_id=department["_id"],
            reported_by=reporter["_id"],  # from the logged-in user, never from the form
            photo_url=photo_url,
            latitude=latitude,
            longitude=longitude,
            is_anonymous=is_anonymous,
        )
        await db[COMPLAINTS_COLLECTION].insert_one(document)
    except Exception:
        await storage.delete(photo_url)  # don't leave a photo that belongs to no complaint
        raise

    return to_public_complaint(document, category, department)


async def list_complaints(*, user: dict, status: ComplaintStatus | None, page: int, limit: int) -> dict:
    db = get_database()
    query: dict = {}
    if user["role"] == Role.CITIZEN.value:
        query["reportedBy"] = user["_id"]  # citizens only see their own complaints
    if status is not None:
        query["status"] = status.value

    complaints_collection = db[COMPLAINTS_COLLECTION]
    total = await complaints_collection.count_documents(query)
    cursor = (
        complaints_collection.find(query)
        .sort("createdAt", -1)
        .skip((page - 1) * limit)
        .limit(limit)
    )
    complaints = await cursor.to_list()
    return {
        "items": await _to_public_list(db, complaints),
        "page": page,
        "limit": limit,
        "total": total,
    }


async def get_complaint_for_user(complaint_id: str, user: dict) -> dict:
    db = get_database()
    object_id = parse_object_id(complaint_id, "complaint id")
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": object_id})

    is_owner = complaint is not None and complaint["reportedBy"] == user["_id"]
    if complaint is None or (user["role"] == Role.CITIZEN.value and not is_owner):
        # Same answer for "doesn't exist" and "belongs to someone else"
        raise ApiError(404, "Complaint not found")

    return (await _to_public_list(db, [complaint]))[0]
