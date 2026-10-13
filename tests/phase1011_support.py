"""Helpers shared by the Phase 10 (admin) and Phase 11 (security) tests."""
import pytest
from bson import ObjectId

ADMIN_URL = "/api/v1/admin"


@pytest.fixture(autouse=True)
def clean_phase1011(sync_db):
    """The shared conftest does not know these collections, so empty them for every test."""
    for name in ("notifications", "points_ledger", "audit_logs"):
        sync_db[name].delete_many({})


def make_admin(create_user, email="admin@example.com"):
    return create_user(email=email, role="ADMIN")


def department_id(sync_db, code="ROAD"):
    return str(sync_db["departments"].find_one({"code": code})["_id"])


def category_id(sync_db, code="POTHOLE"):
    return str(sync_db["categories"].find_one({"code": code})["_id"])


def user_by_email(sync_db, email):
    return sync_db["users"].find_one({"email": email})


def audit_entries(sync_db, action=None):
    query = {"action": action} if action else {}
    # Oldest first. Without an explicit sort MongoDB may return any order.
    return list(sync_db["audit_logs"].find(query).sort("_id", 1))


def stored_complaint(sync_db, complaint_id):
    return sync_db["complaints"].find_one({"_id": ObjectId(complaint_id)})
