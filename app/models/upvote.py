from datetime import datetime, timezone

UPVOTES_COLLECTION = "upvotes"


def build_upvote_document(*, complaint_id, user_id) -> dict:
    return {
        "complaintId": complaint_id,
        "userId": user_id,
        "createdAt": datetime.now(timezone.utc),
    }


async def create_upvote_indexes(db) -> None:
    # One upvote per user per complaint. MongoDB itself refuses the second one.
    await db[UPVOTES_COLLECTION].create_index([("userId", 1), ("complaintId", 1)], unique=True)
    await db[UPVOTES_COLLECTION].create_index("complaintId")
