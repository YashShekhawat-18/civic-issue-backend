"""Small helpers shared by the Phase 6 (worker) and Phase 7 (notification) tests."""
import pytest
from bson import ObjectId
from civic_test_helpers import complaint_form, post_complaint

WORKER_URL = "/api/v1/worker/complaints"
NOTIFICATIONS_URL = "/api/v1/notifications"


@pytest.fixture(autouse=True)
def clean_notifications(clean_collections, sync_db):
    """The shared conftest does not know the notifications collection, so empty it here."""
    sync_db["notifications"].delete_many({})


@pytest.fixture(autouse=True)
def seeded(clean_notifications, seed_catalog_only):
    seed_catalog_only()


def make_worker(create_user, sync_db, email="worker@example.com", department_code="ROAD"):
    """Creates a WORKER account linked to a department and returns its auth headers."""
    headers = create_user(email=email, role="WORKER")
    department = sync_db["departments"].find_one({"code": department_code})
    sync_db["users"].update_one({"email": email}, {"$set": {"departmentId": department["_id"]}})
    return headers


def make_complaint(client, headers, sync_db, code="POTHOLE", spot=0, **changes):
    """Citizen reports a complaint (POTHOLE belongs to the ROAD department). Returns its id."""
    response = post_complaint(client, headers, complaint_form(sync_db, code=code, spot=spot, **changes))
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def set_status(client, headers, complaint_id, status, **extra):
    return client.patch(
        f"{WORKER_URL}/{complaint_id}/status", json={"status": status, **extra}, headers=headers
    )


def stored_complaint(sync_db, complaint_id):
    return sync_db["complaints"].find_one({"_id": ObjectId(complaint_id)})
