from datetime import datetime, timezone
from enum import Enum


class PointsEvent(str, Enum):
    COMPLAINT_CREATED = "COMPLAINT_CREATED"
    COMPLAINT_UPVOTED = "COMPLAINT_UPVOTED"
    COMPLAINT_RESOLVED = "COMPLAINT_RESOLVED"


POINTS_LEDGER_COLLECTION = "points_ledger"


def build_ledger_entry(*, user_id, event: PointsEvent, complaint_id, points: int) -> dict:
    return {
        "userId": user_id,
        "event": event.value,
        "complaintId": complaint_id,
        "points": points,
        "createdAt": datetime.now(timezone.utc),
    }


async def create_points_ledger_indexes(db) -> None:
    ledger = db[POINTS_LEDGER_COLLECTION]
    # One reward per user + event + complaint, ever. This is what stops points farming
    # (for example upvote, un-upvote, upvote again), even if two requests arrive together.
    await ledger.create_index([("userId", 1), ("event", 1), ("complaintId", 1)], unique=True)
    await ledger.create_index([("userId", 1), ("createdAt", -1)])
