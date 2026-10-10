"""Finds complaints that were not resolved in time and marks them overdue.

Rule (from the project spec): status is not RESOLVED, createdAt is older than OVERDUE_DAYS,
and overdue is still false  ->  set overdue = true and tell the admins.
"""
import logging
from datetime import datetime, timedelta, timezone

from pymongo import ReturnDocument

from app.core.config import settings
from app.core.database import get_database
from app.models.complaint import ACTIVE_STATUSES, COMPLAINTS_COLLECTION
from app.models.department import DEPARTMENTS_COLLECTION
from app.models.notification import NotificationType
from app.models.user import USERS_COLLECTION, Role
from app.services import notification_service

logger = logging.getLogger("uvicorn.error")  # shows up in the uvicorn terminal

MAX_PER_RUN = 500  # a safety limit; anything left is picked up by the next run


async def mark_overdue_complaints(db=None, now: datetime | None = None) -> dict:
    """Runs one overdue check. Safe to run again and again (it never marks a complaint twice)."""
    if db is None:
        db = get_database()
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=settings.overdue_days)
    complaints = db[COMPLAINTS_COLLECTION]

    candidates = await (
        complaints.find({"status": {"$in": ACTIVE_STATUSES}, "createdAt": {"$lt": cutoff}, "overdue": False})
        .sort("createdAt", 1)
        .limit(MAX_PER_RUN)
        .to_list()
    )
    if not candidates:
        return {"checked": 0, "markedOverdue": 0}

    admins = await db[USERS_COLLECTION].find({"role": Role.ADMIN.value, "isActive": True}).to_list()
    departments = {
        d["_id"]: d
        for d in await db[DEPARTMENTS_COLLECTION]
        .find({"_id": {"$in": list({c["departmentId"] for c in candidates})}})
        .to_list()
    }

    marked = 0
    for candidate in candidates:
        # The filter repeats "overdue is False". If two copies of the job run at the same time,
        # only ONE of them flips the flag and sends the notifications.
        flipped = await complaints.find_one_and_update(
            {"_id": candidate["_id"], "overdue": False, "status": {"$in": ACTIVE_STATUSES}},
            {"$set": {"overdue": True, "updatedAt": now}},
            return_document=ReturnDocument.AFTER,
        )
        if flipped is None:
            continue
        marked += 1

        department = departments.get(flipped["departmentId"])
        message = (
            f"Complaint {flipped['complaintNumber']} ({flipped['title']}) is overdue. "
            f"It has not been resolved after {settings.overdue_days} days. "
            f"Department: {department['name'] if department else 'unknown'}."
        )
        for admin in admins:
            await notification_service.create_notification(
                db,
                user_id=admin["_id"],
                complaint_id=flipped["_id"],
                type=NotificationType.COMPLAINT_OVERDUE,
                title="Complaint is overdue",
                message=message,
            )

    logger.info("Overdue check: %s complaint(s) marked overdue", marked)
    return {"checked": len(candidates), "markedOverdue": marked}
