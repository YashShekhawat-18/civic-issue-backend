"""In-app notifications (saved in MongoDB) plus the optional email copy."""
import logging

from fastapi import BackgroundTasks
from pymongo import ReturnDocument

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.complaint import ComplaintStatus
from app.models.notification import (
    NOTIFICATIONS_COLLECTION,
    NotificationType,
    build_notification_document,
)
from app.models.user import USERS_COLLECTION
from app.services import email_service

logger = logging.getLogger("civic.notifications")

STATUS_TITLES = {
    ComplaintStatus.IN_PROGRESS: "Work has started on your complaint",
    ComplaintStatus.RESOLVED: "Your complaint has been resolved",
}


def to_public_notification(notification: dict) -> dict:
    complaint_id = notification.get("complaintId")
    return {
        "id": str(notification["_id"]),
        "type": notification["type"],
        "title": notification["title"],
        "message": notification["message"],
        "complaintId": str(complaint_id) if complaint_id else None,
        "isRead": notification["isRead"],
        "createdAt": notification["createdAt"],
    }


async def create_notification(db, *, user_id, complaint_id, type: NotificationType, title: str, message: str) -> dict:
    document = build_notification_document(
        user_id=user_id, complaint_id=complaint_id, type=type, title=title, message=message
    )
    await db[NOTIFICATIONS_COLLECTION].insert_one(document)
    return document


async def notify_status_change(
    *,
    complaint: dict,
    department: dict | None,
    new_status: ComplaintStatus,
    note: str | None,
    background_tasks: BackgroundTasks,
) -> None:
    """Tells the citizen who reported the complaint that its status changed.

    Called AFTER the status was saved. Anything that goes wrong in here is logged and
    swallowed, because the status change itself already succeeded.
    """
    try:
        db = get_database()
        department_name = department["name"] if department else "responsible"
        title = STATUS_TITLES[new_status]
        if new_status == ComplaintStatus.IN_PROGRESS:
            message = (
                f"Complaint {complaint['complaintNumber']} ({complaint['title']}) is now being "
                f"worked on by the {department_name} department."
            )
        else:
            message = f"Complaint {complaint['complaintNumber']} ({complaint['title']}) has been marked as resolved."
        if note:
            message += f" Note from the department: {note}"

        await create_notification(
            db,
            user_id=complaint["reportedBy"],
            complaint_id=complaint["_id"],
            type=NotificationType.STATUS_CHANGED,
            title=title,
            message=message,
        )

        if email_service.is_email_enabled():
            reporter = await db[USERS_COLLECTION].find_one({"_id": complaint["reportedBy"]})
            if reporter and reporter.get("isActive") and reporter.get("email"):
                subject = f"[{complaint['complaintNumber']}] {title}"
                body = f"Hello {reporter['name']},\n\n{message}\n\nCivic Issue Reporting System"
                background_tasks.add_task(email_service.send_email, reporter["email"], subject, body)
    except Exception:
        logger.exception("Could not create the status notification for %s", complaint.get("complaintNumber"))


async def list_notifications(*, user: dict, unread_only: bool, page: int, limit: int) -> dict:
    notifications = get_database()[NOTIFICATIONS_COLLECTION]
    query: dict = {"userId": user["_id"]}  # always the logged-in user, never taken from the URL
    if unread_only:
        query["isRead"] = False

    total = await notifications.count_documents(query)
    unread_count = await notifications.count_documents({"userId": user["_id"], "isRead": False})
    cursor = notifications.find(query).sort("createdAt", -1).skip((page - 1) * limit).limit(limit)
    items = [to_public_notification(n) for n in await cursor.to_list()]
    return {"items": items, "page": page, "limit": limit, "total": total, "unreadCount": unread_count}


async def mark_as_read(*, user: dict, notification_id: str) -> dict:
    object_id = parse_object_id(notification_id, "notification id")
    # The filter contains userId, so nobody can mark someone else's notification.
    updated = await get_database()[NOTIFICATIONS_COLLECTION].find_one_and_update(
        {"_id": object_id, "userId": user["_id"]},
        {"$set": {"isRead": True}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:
        raise ApiError(404, "Notification not found")
    return to_public_notification(updated)


async def mark_all_as_read(*, user: dict) -> dict:
    result = await get_database()[NOTIFICATIONS_COLLECTION].update_many(
        {"userId": user["_id"], "isRead": False}, {"$set": {"isRead": True}}
    )
    return {"updated": result.modified_count}
