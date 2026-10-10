"""Points and badges. All the rules live here, not in routes.

How a reward works:
  1. Write a line in the points ledger. A unique index allows each (user, event, complaint)
     only once, so the same action can never pay twice.
  2. Add the points to the user with an atomic $inc.
  3. Give every active badge whose pointsRequired the user has now reached.

award_points() NEVER raises: failing to give points must not break the action that earned them.
"""
import logging

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import get_database
from app.models.badge import BADGES_COLLECTION
from app.models.notification import NotificationType
from app.models.points_ledger import POINTS_LEDGER_COLLECTION, PointsEvent, build_ledger_entry
from app.models.user import USERS_COLLECTION, Role
from app.services import notification_service

logger = logging.getLogger("civic.gamification")


def points_for(event: PointsEvent) -> int:
    """Read at call time, so the amounts follow the .env settings."""
    return {
        PointsEvent.COMPLAINT_CREATED: settings.points_complaint_created,
        PointsEvent.COMPLAINT_UPVOTED: settings.points_complaint_upvoted,
        PointsEvent.COMPLAINT_RESOLVED: settings.points_complaint_resolved,
    }[event]


async def award_points(*, user_id, event: PointsEvent, complaint_id, db=None) -> dict | None:
    """Returns {"pointsAdded", "totalPoints", "newBadges"}, or None if nothing was awarded."""
    try:
        return await _award_points(user_id=user_id, event=event, complaint_id=complaint_id, db=db)
    except Exception:
        logger.exception("Could not award points for %s", event.value)
        return None


async def _award_points(*, user_id, event: PointsEvent, complaint_id, db=None) -> dict | None:
    if db is None:
        db = get_database()
    points = points_for(event)
    if points <= 0:
        return None

    try:
        await db[POINTS_LEDGER_COLLECTION].insert_one(
            build_ledger_entry(user_id=user_id, event=event, complaint_id=complaint_id, points=points)
        )
    except DuplicateKeyError:
        return None  # this user was already rewarded for this event on this complaint

    user = await db[USERS_COLLECTION].find_one_and_update(
        {"_id": user_id},
        {"$inc": {"points": points}},
        return_document=ReturnDocument.AFTER,
    )
    if user is None:
        return None

    new_badges = await _award_badges(db, user)
    return {"pointsAdded": points, "totalPoints": user["points"], "newBadges": new_badges}


async def _award_badges(db, user: dict) -> list[str]:
    reached = (
        await db[BADGES_COLLECTION]
        .find({"isActive": True, "pointsRequired": {"$lte": user["points"]}})
        .sort("pointsRequired", 1)
        .to_list()
    )
    earned_now = []
    for badge in reached:
        if badge["name"] in user.get("badges", []):
            continue
        # "badges != name" in the filter: if two requests race, only one of them adds the badge.
        result = await db[USERS_COLLECTION].update_one(
            {"_id": user["_id"], "badges": {"$ne": badge["name"]}},
            {"$addToSet": {"badges": badge["name"]}},
        )
        if result.modified_count == 1:
            earned_now.append(badge["name"])
            await notification_service.create_notification(
                db,
                user_id=user["_id"],
                complaint_id=None,
                type=NotificationType.BADGE_EARNED,
                title=f"New badge: {badge['name']}",
                message=f"You earned the \"{badge['name']}\" badge. {badge['description']}",
            )
    return earned_now


def _public_badge(badge: dict) -> dict:
    return {
        "name": badge["name"],
        "description": badge["description"],
        "icon": badge["icon"],
        "pointsRequired": badge["pointsRequired"],
    }


async def list_badges() -> list[dict]:
    cursor = get_database()[BADGES_COLLECTION].find({"isActive": True}).sort("pointsRequired", 1)
    return [_public_badge(b) for b in await cursor.to_list()]


async def get_my_summary(user: dict) -> dict:
    db = get_database()
    all_badges = await db[BADGES_COLLECTION].find({"isActive": True}).sort("pointsRequired", 1).to_list()
    earned_names = set(user.get("badges", []))
    next_badge = next((b for b in all_badges if b["pointsRequired"] > user["points"]), None)

    ledger = db[POINTS_LEDGER_COLLECTION].find({"userId": user["_id"]}).sort("createdAt", -1).limit(10)
    recent = [
        {
            "event": entry["event"],
            "points": entry["points"],
            "complaintId": str(entry["complaintId"]),
            "createdAt": entry["createdAt"],
        }
        for entry in await ledger.to_list()
    ]
    return {
        "points": user["points"],
        "badges": [_public_badge(b) for b in all_badges if b["name"] in earned_names],
        "nextBadge": (
            {**_public_badge(next_badge), "pointsNeeded": next_badge["pointsRequired"] - user["points"]}
            if next_badge
            else None
        ),
        "recentActivity": recent,
    }


async def get_leaderboard(limit: int) -> list[dict]:
    """Top citizens by points. Only the name is shown (no email, phone or id)."""
    cursor = (
        get_database()[USERS_COLLECTION]
        .find({"role": Role.CITIZEN.value, "isActive": True, "points": {"$gt": 0}})
        .sort("points", -1)
        .limit(limit)
    )
    users = await cursor.to_list()
    return [
        {"rank": position, "name": u["name"], "points": u["points"], "badgeCount": len(u.get("badges", []))}
        for position, u in enumerate(users, start=1)
    ]
