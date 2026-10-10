"""Changing a complaint's status. Used by the worker portal."""
from datetime import datetime, timezone

from fastapi import BackgroundTasks
from pymongo import ReturnDocument

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.complaint import ALLOWED_TRANSITIONS, COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.points_ledger import PointsEvent
from app.services import gamification_service, notification_service, worker_service


async def change_status(
    *,
    complaint_id: str,
    new_status: ComplaintStatus,
    note: str | None,
    worker: dict,
    background_tasks: BackgroundTasks,
) -> dict:
    db = get_database()
    complaints = db[COMPLAINTS_COLLECTION]
    object_id = parse_object_id(complaint_id, "complaint id")
    department_id = worker_service.require_department_id(worker)

    # 1. The complaint must belong to the worker's department.
    complaint = await complaints.find_one({"_id": object_id, "departmentId": department_id})
    if complaint is None:
        raise ApiError(404, "Complaint not found")

    # 2. The status change must be one of the allowed transitions.
    current_status = ComplaintStatus(complaint["status"])
    if new_status not in ALLOWED_TRANSITIONS[current_status]:
        allowed = [s.value for s in ALLOWED_TRANSITIONS[current_status]]
        hint = f"Allowed next status: {', '.join(allowed)}" if allowed else "This complaint is already resolved"
        raise ApiError(
            409,
            f"Cannot change status from {current_status.value} to {new_status.value}. {hint}",
        )

    now = datetime.now(timezone.utc)
    changes: dict = {"status": new_status.value, "updatedAt": now}
    if new_status == ComplaintStatus.IN_PROGRESS:
        changes["assignedWorker"] = worker["_id"]  # the worker who starts the job owns it
    if new_status == ComplaintStatus.RESOLVED:
        changes["resolvedAt"] = now

    # 3. Save it. The filter repeats the status we just checked, so if two workers click at the
    #    same moment only ONE update matches. The other gets None and a clear 409 message.
    updated = await complaints.find_one_and_update(
        {"_id": object_id, "departmentId": department_id, "status": current_status.value},
        {"$set": changes},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise ApiError(409, "This complaint was just updated by someone else. Please refresh and try again")

    # 4. Tell the citizen (in-app + email). Never fails the request.
    department = await db[DEPARTMENTS_COLLECTION].find_one({"_id": department_id})
    await notification_service.notify_status_change(
        complaint=updated,
        department=department,
        new_status=new_status,
        note=note,
        background_tasks=background_tasks,
    )

    # 5. Reward the citizen whose complaint got resolved. Never raises.
    if new_status == ComplaintStatus.RESOLVED:
        await gamification_service.award_points(
            user_id=updated["reportedBy"], event=PointsEvent.COMPLAINT_RESOLVED, complaint_id=updated["_id"], db=db
        )

    return (await worker_service.to_worker_views(db, [updated]))[0]
