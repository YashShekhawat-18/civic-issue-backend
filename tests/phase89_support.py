"""Helpers shared by the Phase 8 (overdue) and Phase 9 (points and badges) tests."""
import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.models.badge import build_badge_document

OVERDUE_URL = "/api/v1/admin/overdue"
GAMIFICATION_URL = "/api/v1/gamification"

BADGES = [
    ("Newcomer", "Earned your first points", "star", 10),
    ("Active Citizen", "Regularly helping your city", "medal", 50),
    ("Community Helper", "A trusted voice in your community", "trophy", 150),
    ("City Champion", "Top contributor to a better city", "crown", 500),
]


@pytest.fixture(autouse=True)
def clean_ledger(sync_db):
    """The shared conftest does not know these collections, so empty them for every test."""
    for name in ("notifications", "points_ledger"):
        sync_db[name].delete_many({})


def seed_badges(sync_db):
    for name, description, icon, points_required in BADGES:
        sync_db["badges"].insert_one(
            build_badge_document(name=name, description=description, icon=icon, points_required=points_required)
        )


def run_with_db(function):
    """Runs an async service function against the test database."""

    async def _run():
        mongo = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
        try:
            return await function(mongo[settings.mongo_db_name])
        finally:
            await mongo.close()

    return asyncio.run(_run())


def make_old(sync_db, complaint_id, days):
    """Pretends the complaint was reported `days` days ago."""
    sync_db["complaints"].update_one(
        {"_id": ObjectId(complaint_id)},
        {"$set": {"createdAt": datetime.now(timezone.utc) - timedelta(days=days)}},
    )


def user_doc(sync_db, email):
    return sync_db["users"].find_one({"email": email})
