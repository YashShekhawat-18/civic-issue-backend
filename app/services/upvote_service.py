from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.object_id import parse_object_id
from app.models.complaint import COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.points_ledger import PointsEvent
from app.models.upvote import UPVOTES_COLLECTION, build_upvote_document
from app.services import gamification_service


async def _get_complaint_or_404(db, complaint_id: str) -> dict:
    object_id = parse_object_id(complaint_id, "complaint id")
    complaint = await db[COMPLAINTS_COLLECTION].find_one({"_id": object_id})
    if complaint is None:
        raise ApiError(404, "Complaint not found")
    return complaint


async def add_upvote(complaint_id: str, user_id: ObjectId, db=None) -> dict:
    if db is None:
        db = get_database()
    complaint = await _get_complaint_or_404(db, complaint_id)

    if complaint["reportedBy"] == user_id:
        raise ApiError(403, "You cannot upvote your own complaint")
    if complaint["status"] == ComplaintStatus.RESOLVED.value:
        raise ApiError(409, "This complaint is already resolved")

    # Step 1: save the upvote. The unique index (userId + complaintId) rejects a second one,
    # even if two requests arrive at the same instant.
    try:
        await db[UPVOTES_COLLECTION].insert_one(
            build_upvote_document(complaint_id=complaint["_id"], user_id=user_id)
        )
    except DuplicateKeyError:
        raise ApiError(409, "You have already upvoted this complaint")

    # Step 2: add 1 to the counter in a single atomic MongoDB operation
    updated = await db[COMPLAINTS_COLLECTION].find_one_and_update(
        {"_id": complaint["_id"]},
        {"$inc": {"upvoteCount": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if updated is None:  # the complaint disappeared in between: undo step 1
        await db[UPVOTES_COLLECTION].delete_one({"complaintId": complaint["_id"], "userId": user_id})
        raise ApiError(404, "Complaint not found")

    # Points for the upvoter, once per complaint (the ledger ignores repeats). Never raises.
    await gamification_service.award_points(
        user_id=user_id, event=PointsEvent.COMPLAINT_UPVOTED, complaint_id=complaint["_id"], db=db
    )

    return {"complaintId": str(complaint["_id"]), "upvoteCount": updated["upvoteCount"], "hasUpvoted": True}


async def remove_upvote(complaint_id: str, user_id: ObjectId, db=None) -> dict:
    if db is None:
        db = get_database()
    complaint = await _get_complaint_or_404(db, complaint_id)

    result = await db[UPVOTES_COLLECTION].delete_one({"complaintId": complaint["_id"], "userId": user_id})
    if result.deleted_count == 0:
        raise ApiError(404, "You have not upvoted this complaint")

    # "upvoteCount > 0" in the filter means the counter can never go below zero
    updated = await db[COMPLAINTS_COLLECTION].find_one_and_update(
        {"_id": complaint["_id"], "upvoteCount": {"$gt": 0}},
        {"$inc": {"upvoteCount": -1}},
        return_document=ReturnDocument.AFTER,
    )
    upvote_count = updated["upvoteCount"] if updated else 0

    return {"complaintId": str(complaint["_id"]), "upvoteCount": upvote_count, "hasUpvoted": False}
