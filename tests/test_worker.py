import pytest
from bson import ObjectId
from phase67_support import (  # noqa: F401  (the fixtures must be imported to be active)
    WORKER_URL,
    clean_notifications,
    make_complaint,
    make_worker,
    seeded,
    set_status,
    stored_complaint,
)


# ---------- who may use the worker portal ----------

def test_worker_routes_need_login(client):
    assert client.get(WORKER_URL).status_code == 401


def test_citizen_cannot_use_worker_routes(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    assert client.get(WORKER_URL, headers=citizen).status_code == 403
    assert client.get(f"{WORKER_URL}/{complaint_id}", headers=citizen).status_code == 403
    assert set_status(client, citizen, complaint_id, "IN_PROGRESS").status_code == 403
    assert stored_complaint(sync_db, complaint_id)["status"] == "SUBMITTED"


def test_admin_cannot_use_worker_routes(client, create_user):
    admin = create_user(email="admin@example.com", role="ADMIN")
    assert client.get(WORKER_URL, headers=admin).status_code == 403


def test_worker_without_department_is_refused(client, create_user):
    worker = create_user(email="nodept@example.com", role="WORKER")
    response = client.get(WORKER_URL, headers=worker)
    assert response.status_code == 403
    assert "department" in response.json()["message"]


# ---------- list and detail ----------

def test_worker_sees_only_own_department(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    road_id = make_complaint(client, citizen, sync_db, code="POTHOLE", spot=0)
    make_complaint(client, citizen, sync_db, code="GARBAGE", spot=1)  # Sanitation department

    road_worker = make_worker(create_user, sync_db, "road@example.com", "ROAD")
    data = client.get(WORKER_URL, headers=road_worker).json()["data"]
    assert data["total"] == 1
    assert [item["id"] for item in data["items"]] == [road_id]
    assert data["items"][0]["department"]["code"] == "ROAD"
    assert data["items"][0]["category"]["code"] == "POTHOLE"


def test_list_contains_everything_a_worker_needs(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    item = client.get(WORKER_URL, headers=worker).json()["data"]["items"][0]
    assert item["location"]["type"] == "Point"
    assert len(item["location"]["coordinates"]) == 2
    assert item["photoUrl"]
    assert item["status"] == "SUBMITTED"
    assert item["allowedNextStatuses"] == ["IN_PROGRESS"]


def test_worker_detail_hides_reporter_contact_details(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    data = client.get(f"{WORKER_URL}/{complaint_id}", headers=worker).json()["data"]
    assert data["reporter"] == {"name": "Test User"}
    assert "reportedBy" not in data
    assert "citizen@example.com" not in str(data)


def test_anonymous_reporter_is_hidden_from_worker(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db, isAnonymous="true")
    worker = make_worker(create_user, sync_db)
    data = client.get(f"{WORKER_URL}/{complaint_id}", headers=worker).json()["data"]
    assert data["isAnonymous"] is True
    assert data["reporter"] is None


def test_worker_cannot_open_another_departments_complaint(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    sanitation_id = make_complaint(client, citizen, sync_db, code="GARBAGE")
    road_worker = make_worker(create_user, sync_db, "road@example.com", "ROAD")
    # Same 404 as a complaint that does not exist, so ids of other departments cannot be probed
    assert client.get(f"{WORKER_URL}/{sanitation_id}", headers=road_worker).status_code == 404
    assert client.get(f"{WORKER_URL}/{ObjectId()}", headers=road_worker).status_code == 404


def test_invalid_complaint_id_is_400(client, create_user, sync_db):
    worker = make_worker(create_user, sync_db)
    assert client.get(f"{WORKER_URL}/not-an-id", headers=worker).status_code == 400


def test_filter_by_status_and_assigned_to_me(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    first = make_complaint(client, citizen, sync_db, spot=0)
    make_complaint(client, citizen, sync_db, spot=1)
    worker = make_worker(create_user, sync_db)
    other_worker = make_worker(create_user, sync_db, "other@example.com")
    set_status(client, worker, first, "IN_PROGRESS")

    in_progress = client.get(f"{WORKER_URL}?status=IN_PROGRESS", headers=worker).json()["data"]
    assert [i["id"] for i in in_progress["items"]] == [first]
    assert client.get(f"{WORKER_URL}?status=SUBMITTED", headers=worker).json()["data"]["total"] == 1

    mine = client.get(f"{WORKER_URL}?assignedToMe=true", headers=worker).json()["data"]
    assert [i["id"] for i in mine["items"]] == [first]
    assert client.get(f"{WORKER_URL}?assignedToMe=true", headers=other_worker).json()["data"]["total"] == 0
    assert client.get(f"{WORKER_URL}?status=WRONG", headers=worker).status_code == 422


def test_filter_overdue_and_pagination(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    ids = [make_complaint(client, citizen, sync_db, spot=spot) for spot in range(3)]
    sync_db["complaints"].update_one({"_id": ObjectId(ids[0])}, {"$set": {"overdue": True}})
    worker = make_worker(create_user, sync_db)

    overdue = client.get(f"{WORKER_URL}?overdue=true", headers=worker).json()["data"]
    assert [i["id"] for i in overdue["items"]] == [ids[0]]

    page = client.get(f"{WORKER_URL}?limit=2&page=2", headers=worker).json()["data"]
    assert page["total"] == 3
    assert len(page["items"]) == 1
    assert client.get(f"{WORKER_URL}?limit=500", headers=worker).status_code == 422


# ---------- status transitions ----------

def test_full_workflow_submitted_to_in_progress_to_resolved(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)

    started = set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert started.status_code == 200
    data = started.json()["data"]
    assert data["status"] == "IN_PROGRESS"
    assert data["assignedWorker"]["name"] == "Test User"
    assert data["allowedNextStatuses"] == ["RESOLVED"]
    assert data["resolvedAt"] is None

    resolved = set_status(client, worker, complaint_id, "RESOLVED")
    assert resolved.status_code == 200
    data = resolved.json()["data"]
    assert data["status"] == "RESOLVED"
    assert data["resolvedAt"] is not None
    assert data["allowedNextStatuses"] == []

    stored = stored_complaint(sync_db, complaint_id)
    assert stored["status"] == "RESOLVED"
    assert stored["resolvedAt"] is not None


def test_citizen_sees_the_new_status(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    data = client.get(f"/api/v1/complaints/{complaint_id}", headers=citizen).json()["data"]
    assert data["status"] == "IN_PROGRESS"


@pytest.mark.parametrize(
    "start, target",
    [
        ("SUBMITTED", "RESOLVED"),      # cannot skip a step
        ("SUBMITTED", "SUBMITTED"),     # not a change
        ("IN_PROGRESS", "SUBMITTED"),   # cannot go backwards
        ("IN_PROGRESS", "IN_PROGRESS"),
        ("RESOLVED", "IN_PROGRESS"),    # resolved is final
        ("RESOLVED", "SUBMITTED"),
        ("RESOLVED", "RESOLVED"),
    ],
)
def test_invalid_transitions_are_rejected(client, create_user, sync_db, start, target):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    sync_db["complaints"].update_one({"_id": ObjectId(complaint_id)}, {"$set": {"status": start}})

    response = set_status(client, worker, complaint_id, target)
    assert response.status_code == 409
    assert "Cannot change status" in response.json()["message"]
    assert stored_complaint(sync_db, complaint_id)["status"] == start  # nothing changed
    assert sync_db["notifications"].count_documents({}) == 0          # and nobody was notified


def test_same_request_twice_second_one_fails(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    assert set_status(client, worker, complaint_id, "IN_PROGRESS").status_code == 200
    assert set_status(client, worker, complaint_id, "IN_PROGRESS").status_code == 409
    assert sync_db["notifications"].count_documents({}) == 1  # only one notification was created


def test_worker_cannot_change_another_departments_complaint(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    sanitation_id = make_complaint(client, citizen, sync_db, code="GARBAGE")
    road_worker = make_worker(create_user, sync_db, "road@example.com", "ROAD")
    assert set_status(client, road_worker, sanitation_id, "IN_PROGRESS").status_code == 404
    assert stored_complaint(sync_db, sanitation_id)["status"] == "SUBMITTED"


def test_status_request_is_validated(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    assert set_status(client, worker, complaint_id, "DONE").status_code == 422
    assert set_status(client, worker, complaint_id, "IN_PROGRESS", note="x" * 501).status_code == 422
    assert set_status(client, worker, complaint_id, "IN_PROGRESS", assignedWorker="abc").status_code == 422
    assert client.patch(f"{WORKER_URL}/{complaint_id}/status", json={}, headers=worker).status_code == 422
    assert client.patch(f"{WORKER_URL}/bad-id/status", json={"status": "IN_PROGRESS"}, headers=worker).status_code == 400
    assert stored_complaint(sync_db, complaint_id)["status"] == "SUBMITTED"


def test_lost_race_returns_409(client, create_user, sync_db, monkeypatch):
    """If the status changes between the check and the save, the atomic update refuses it."""
    from app.services import status_service

    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)

    class RacingCollection:
        """Behaves like the real collection, but another worker 'wins' right after the first read."""

        def __init__(self, real):
            self._real = real

        async def find_one(self, *args, **kwargs):
            found = await self._real.find_one(*args, **kwargs)
            sync_db["complaints"].update_one({"_id": ObjectId(complaint_id)}, {"$set": {"status": "IN_PROGRESS"}})
            return found

        def __getattr__(self, name):
            return getattr(self._real, name)

    class RacingDatabase:
        def __init__(self, real):
            self._real = real

        def __getitem__(self, name):
            collection = self._real[name]
            return RacingCollection(collection) if name == "complaints" else collection

    real_get_database = status_service.get_database
    monkeypatch.setattr(status_service, "get_database", lambda: RacingDatabase(real_get_database()))

    response = set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert response.status_code == 409
    assert "refresh" in response.json()["message"]
    assert sync_db["notifications"].count_documents({}) == 0
