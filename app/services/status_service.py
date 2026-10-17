"""Changing a complaint's status. Used by the worker portal and by admins."""
from datetime import datetime, timezone

from fastapi import BackgroundTasks, UploadFile
from pymongo import ReturnDocument

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.audit_log import AuditAction
from app.models.complaint import ALLOWED_TRANSITIONS, COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.points_ledger import PointsEvent
from app.models.user import Role
from app.services import (
    audit_service,
    gamification_service,
    image_service,
    notification_service,
    worker_service,
)
from app.storage import get_storage

RESOLUTION_PHOTO_FOLDER = "resolutions"


def ensure_transition_allowed(current_status: ComplaintStatus, new_status: ComplaintStatus) -> None:
    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        allowed = [s.value for s in ALLOWED_TRANSITIONS[current_status]]
        hint = f"Allowed next status: {', '.join(allowed)}" if allowed else "This complaint is already resolved"
        raise ApiError(
            409,
            f"Cannot change status from {current_status.value} to {new_status.value}. {hint}",
        )


async def change_status(
    *,
    complaint_id: str,
    new_status: ComplaintStatus,
    note: str | None,
    worker: dict,
    background_tasks: BackgroundTasks,
    extra_changes: dict | None = None,
) -> dict:
    db = get_database()
    complaints = db[COMPLAINTS_COLLECTION]
    object_id = parse_object_id(complaint_id, "complaint id")
    is_admin = worker["role"] == Role.ADMIN.value
    # A worker is tied to their own department. An admin may change any complaint.
    department_id = None if is_admin else worker_service.require_department_id(worker)
    scope = {"_id": object_id} if is_admin else {"_id": object_id, "departmentId": department_id}

    # 1. The complaint must belong to the worker's department (admins: any department).
    complaint = await complaints.find_one(scope)
    if complaint is None:
        raise ApiError(404, "Complaint not found")

    # 2. The status change must be one of the allowed transitions.
    current_status = ComplaintStatus(complaint["status"])
    ensure_transition_allowed(current_status, new_status)

    now = datetime.now(timezone.utc)
    changes: dict = {"status": new_status.value, "updatedAt": now, **(extra_changes or {})}
    if new_status == ComplaintStatus.IN_PROGRESS and not is_admin:
        changes["assignedWorker"] = worker["_id"]  # the worker who starts the job owns it
    if new_status == ComplaintStatus.RESOLVED:
        changes["resolvedAt"] = now

    # 3. Save it. The filter repeats the status we just checked, so if two workers click at the
    #    same moment only ONE update matches. The other gets None and a clear 409 message.
    updated = await complaints.find_one_and_update(
        {**scope, "status": current_status.value},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise ApiError(409, "This complaint was just updated by someone else. Please refresh and try again")

    # 4. Tell the citizen (in-app + email). Never fails the request.
    department = await db[DEPARTMENTS_COLLECTION].find_one({"_id": updated["departmentId"]})
    await notification_service.notify_status_change(
        complaint=updated,
        department=department,
        new_status=new_status,
        note=note,
        background_tasks=background_tasks,
    )

    await audit_service.log_action(
        actor=worker,
        action=AuditAction.STATUS_CHANGED,
        entity="COMPLAINT",
        entity_id=updated["_id"],
        metadata={
            "complaintNumber": updated["complaintNumber"],
            "from": current_status.value,
            "to": new_status.value,
            "byRole": worker["role"],
        },
        db=db,
    )

    # 5. Reward the citizen whose complaint got resolved. Never raises.
    if new_status == ComplaintStatus.RESOLVED:
        await gamification_service.award_points(
            user_id=updated["reportedBy"], event=PointsEvent.COMPLAINT_RESOLVED, complaint_id=updated["_id"], db=db
        )

    return (await worker_service.to_worker_views(db, [updated]))[0]


async def resolve_with_photo(
    *,
    complaint_id: str,
    photo: UploadFile,
    note: str | None,
    worker: dict,
    background_tasks: BackgroundTasks,
) -> dict:
    """A worker marks a complaint RESOLVED. This needs an after-fix photo taken at the place."""
    db = get_database()
    complaint = await worker_service.get_department_complaint_document(worker=worker, complaint_id=complaint_id)
    ensure_transition_allowed(ComplaintStatus(complaint["status"]), ComplaintStatus.RESOLVED)

    longitude, latitude = complaint["location"]["coordinates"]
    content, extension, position = await image_service.read_geotagged_image(
        photo, latitude=latitude, longitude=longitude, place="the reported location"
    )

    storage = get_storage()
    photo_url = await storage.save(content, extension, RESOLUTION_PHOTO_FOLDER)
    location = None if position is None else {"type": "Point", "coordinates": [position[1], position[0]]}
    try:
        return await change_status(
            complaint_id=complaint_id,
            new_status=ComplaintStatus.RESOLVED,
            note=note,
            worker=worker,
            background_tasks=background_tasks,
            extra_changes={"resolutionPhotoUrl": photo_url, "resolutionPhotoLocation": location},
        )
    except Exception:
        await storage.delete(photo_url)  # the status did not change, so do not keep the photo
        raise
