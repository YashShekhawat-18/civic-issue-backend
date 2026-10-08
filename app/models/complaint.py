from datetime import datetime, timezone
from enum import Enum


class ComplaintStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"


class Priority(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


COMPLAINTS_COLLECTION = "complaints"

# "Active" complaints are the ones still open. Only these count as duplicates.
ACTIVE_STATUSES = [ComplaintStatus.SUBMITTED.value, ComplaintStatus.IN_PROGRESS.value]


def build_complaint_document(
    *,
    complaint_number: str,
    title: str,
    description: str,
    category_id,
    department_id,
    reported_by,
    photo_url: str,
    latitude: float,
    longitude: float,
    is_anonymous: bool,
) -> dict:
    now = datetime.now(timezone.utc)
    return {
        "complaintNumber": complaint_number,
        "title": title,
        "description": description,
        "categoryId": category_id,
        "departmentId": department_id,
        "reportedBy": reported_by,
        "assignedWorker": None,
        "photoUrl": photo_url,
        # GeoJSON Point: the order is [longitude, latitude]
        "location": {"type": "Point", "coordinates": [longitude, latitude]},
        "status": ComplaintStatus.SUBMITTED.value,  # always starts as SUBMITTED
        "priority": Priority.MEDIUM.value,
        "isAnonymous": is_anonymous,
        "duplicateOf": None,
        "upvoteCount": 0,
        "overdue": False,
        "resolvedAt": None,
        "createdAt": now,
        "updatedAt": now,
    }


async def create_complaint_indexes(db) -> None:
    complaints = db[COMPLAINTS_COLLECTION]
    await complaints.create_index([("location", "2dsphere")])  # needed for "find nearby" queries
    await complaints.create_index("complaintNumber", unique=True)
    await complaints.create_index("categoryId")
    await complaints.create_index("departmentId")
    await complaints.create_index("status")
    await complaints.create_index("createdAt")
    await complaints.create_index("overdue")
    await complaints.create_index("reportedBy")
