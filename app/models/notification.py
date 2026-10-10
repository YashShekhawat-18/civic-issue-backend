from datetime import datetime, timezone
from enum import Enum


class NotificationType(str, Enum):
    STATUS_CHANGED = "STATUS_CHANGED"
    COMPLAINT_OVERDUE = "COMPLAINT_OVERDUE"  # used later by the overdue job
    BADGE_EARNED = "BADGE_EARNED"            # used later by points and badges


NOTIFICATIONS_COLLECTION = "notifications"


def build_notification_document(
    *, user_id, complaint_id, type: NotificationType, title: str, message: str
) -> dict:
    return {
        "userId": user_id,
        "complaintId": complaint_id,  # None when the notification is not about a complaint
        "type": type.value,
        "title": title,
        "message": message,
        "isRead": False,
        "createdAt": datetime.now(timezone.utc),
    }


async def create_notification_indexes(db) -> None:
    notifications = db[NOTIFICATIONS_COLLECTION]
    # "my newest notifications" and "my unread count" are the two common queries
    await notifications.create_index([("userId", 1), ("createdAt", -1)])
    await notifications.create_index([("userId", 1), ("isRead", 1)])
