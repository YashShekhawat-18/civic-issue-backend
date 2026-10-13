import os

import pytest
from bson import ObjectId
from phase1011_support import (  # noqa: F401
    ADMIN_URL,
    audit_entries,
    category_id,
    clean_phase1011,
    department_id,
    make_admin,
    stored_complaint,
    user_by_email,
)
from phase67_support import clean_notifications, make_complaint, make_worker, seeded, set_status  # noqa: F401
from phase89_support import clean_ledger, make_old  # noqa: F401

from app.core.config import settings

COMPLAINTS_URL = "/api/v1/complaints"


# ---------- list, filters, detail ----------

def test_admin_lists_and_filters_all_complaints(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    pothole = make_complaint(client, citizen, sync_db, code="POTHOLE", spot=0)
    garbage = make_complaint(client, citizen, sync_db, code="GARBAGE", spot=1)
    set_status(client, worker, pothole, "IN_PROGRESS")
    make_old(sync_db, garbage, 5)
    sync_db["complaints"].update_one({"_id": ObjectId(garbage)}, {"$set": {"overdue": True}})

    def ids(query=""):
        data = client.get(f"{ADMIN_URL}/complaints{query}", headers=admin).json()["data"]
        return {item["id"] for item in data["items"]}

    assert ids() == {pothole, garbage}
    assert ids("?status=IN_PROGRESS") == {pothole}
    assert ids("?status=SUBMITTED") == {garbage}
    assert ids("?overdue=true") == {garbage}
    assert ids("?overdue=false") == {pothole}
    assert ids(f"?categoryId={category_id(sync_db, 'GARBAGE')}") == {garbage}
    assert ids(f"?departmentId={department_id(sync_db, 'ROAD')}") == {pothole}
    number = stored_complaint(sync_db, garbage)["complaintNumber"]
    assert ids(f"?number={number.lower()}") == {garbage}
    assert ids(f"?status=IN_PROGRESS&categoryId={category_id(sync_db, 'GARBAGE')}") == set()


def test_list_validation_and_pagination(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    for spot in range(3):
        make_complaint(client, citizen, sync_db, spot=spot)
    page = client.get(f"{ADMIN_URL}/complaints?limit=2&page=2", headers=admin).json()["data"]
    assert page["total"] == 3 and len(page["items"]) == 1
    assert client.get(f"{ADMIN_URL}/complaints?status=NOPE", headers=admin).status_code == 422
    assert client.get(f"{ADMIN_URL}/complaints?categoryId=abc", headers=admin).status_code == 400
    assert client.get(f"{ADMIN_URL}/complaints?limit=51", headers=admin).status_code == 422


def test_admin_detail_shows_reporter_unless_anonymous(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    open_one = make_complaint(client, citizen, sync_db, spot=0)
    hidden = make_complaint(client, citizen, sync_db, spot=1, isAnonymous="true")

    shown = client.get(f"{ADMIN_URL}/complaints/{open_one}", headers=admin).json()["data"]
    assert shown["reporter"]["name"] == "Test User"
    assert shown["reporter"]["id"] == str(user_by_email(sync_db, "citizen@example.com")["_id"])
    assert "citizen@example.com" not in str(shown)

    anonymous = client.get(f"{ADMIN_URL}/complaints/{hidden}", headers=admin).json()["data"]
    assert anonymous["reporter"] is None
    assert str(user_by_email(sync_db, "citizen@example.com")["_id"]) not in str(anonymous)

    assert client.get(f"{ADMIN_URL}/complaints/{ObjectId()}", headers=admin).status_code == 404
    assert client.get(f"{ADMIN_URL}/complaints/bad-id", headers=admin).status_code == 400


# ---------- map ----------

def test_map_returns_small_pins_with_coordinates(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    pothole = make_complaint(client, citizen, sync_db, code="POTHOLE", spot=0)
    make_complaint(client, citizen, sync_db, code="GARBAGE", spot=1)

    response = client.get(f"{ADMIN_URL}/complaints/map", headers=admin)
    assert response.status_code == 200  # "map" is not mistaken for a complaint id
    data = response.json()["data"]
    assert data["count"] == 2
    pin = next(item for item in data["items"] if item["id"] == pothole)
    assert -90 <= pin["latitude"] <= 90 and 72 < pin["longitude"] < 74
    assert pin["category"]["code"] == "POTHOLE" and pin["department"]["code"] == "ROAD"
    assert set(pin) == {"id", "complaintNumber", "title", "status", "priority", "overdue", "upvoteCount",
                        "category", "department", "latitude", "longitude", "createdAt"}
    assert "description" not in pin and "photoUrl" not in pin and "reporter" not in pin

    filtered = client.get(f"{ADMIN_URL}/complaints/map?categoryId={category_id(sync_db, 'GARBAGE')}", headers=admin).json()["data"]
    assert filtered["count"] == 1
    assert client.get(f"{ADMIN_URL}/complaints/map?limit=1", headers=admin).json()["data"]["count"] == 1
    assert client.get(f"{ADMIN_URL}/complaints/map?limit=1001", headers=admin).status_code == 422


# ---------- edit ----------

def patch(client, admin, complaint_id, body):
    return client.patch(f"{COMPLAINTS_URL}/{complaint_id}", json=body, headers=admin)


def test_admin_can_edit_text_and_priority_and_it_is_audited(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)

    response = patch(client, admin, complaint_id, {"title": "Pothole fixed title", "priority": "HIGH"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Pothole fixed title" and data["priority"] == "HIGH"
    assert stored_complaint(sync_db, complaint_id)["priority"] == "HIGH"

    entry = audit_entries(sync_db, "COMPLAINT_UPDATED")[0]
    assert entry["userId"] == user_by_email(sync_db, "admin@example.com")["_id"]
    assert entry["metadata"]["changes"]["priority"] == ["MEDIUM", "HIGH"]
    assert entry["metadata"]["changes"]["title"][1] == "Pothole fixed title"


def test_no_real_change_writes_no_audit_entry(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    assert patch(client, admin, complaint_id, {"priority": "MEDIUM"}).status_code == 200
    assert audit_entries(sync_db, "COMPLAINT_UPDATED") == []


def test_changing_category_moves_the_complaint_to_the_new_department(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    road_worker = make_worker(create_user, sync_db, "road@example.com", "ROAD")
    complaint_id = make_complaint(client, citizen, sync_db, code="POTHOLE")
    set_status(client, road_worker, complaint_id, "IN_PROGRESS")
    assert stored_complaint(sync_db, complaint_id)["assignedWorker"] is not None

    response = patch(client, admin, complaint_id, {"categoryId": category_id(sync_db, "GARBAGE")})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["category"]["code"] == "GARBAGE"
    assert data["department"]["code"] == "SANITATION"  # derived from the category, not from the request
    assert data["assignedWorker"] is None              # the ROAD worker no longer fits
    audit = audit_entries(sync_db, "COMPLAINT_UPDATED")[0]["metadata"]["changes"]
    assert "departmentId" in audit and "assignedWorker" in audit


def test_department_cannot_be_set_directly(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    response = patch(client, admin, complaint_id, {"departmentId": department_id(sync_db, "ELECTRICAL")})
    assert response.status_code == 422
    assert stored_complaint(sync_db, complaint_id)["departmentId"] == ObjectId(department_id(sync_db, "ROAD"))


def test_edit_validation_and_refusals(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)

    assert patch(client, admin, complaint_id, {}).status_code == 422                       # nothing to update
    assert patch(client, admin, complaint_id, {"title": "abc"}).status_code == 422        # too short
    assert patch(client, admin, complaint_id, {"priority": "URGENT"}).status_code == 422
    assert patch(client, admin, complaint_id, {"status": "RESOLVED"}).status_code == 422  # status has its own route
    assert patch(client, admin, complaint_id, {"reportedBy": str(ObjectId())}).status_code == 422
    assert patch(client, admin, complaint_id, {"categoryId": str(ObjectId())}).status_code == 404
    assert patch(client, admin, str(ObjectId()), {"priority": "LOW"}).status_code == 404
    assert patch(client, admin, "bad-id", {"priority": "LOW"}).status_code == 400

    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")
    response = patch(client, admin, complaint_id, {"categoryId": category_id(sync_db, "GARBAGE")})
    assert response.status_code == 409  # resolved complaints keep their category


def test_assign_and_unassign_a_worker(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    make_worker(create_user, sync_db, "road@example.com", "ROAD")
    make_worker(create_user, sync_db, "sanitation@example.com", "SANITATION")
    complaint_id = make_complaint(client, citizen, sync_db, code="POTHOLE")
    road_id = str(user_by_email(sync_db, "road@example.com")["_id"])
    sanitation_id = str(user_by_email(sync_db, "sanitation@example.com")["_id"])

    assert patch(client, admin, complaint_id, {"assignedWorkerId": sanitation_id}).status_code == 409  # wrong department
    assert patch(client, admin, complaint_id, {"assignedWorkerId": str(ObjectId())}).status_code == 404
    assert patch(client, admin, complaint_id, {"assignedWorkerId": str(user_by_email(sync_db, "citizen@example.com")["_id"])}).status_code == 404

    data = patch(client, admin, complaint_id, {"assignedWorkerId": road_id}).json()["data"]
    assert data["assignedWorker"]["id"] == road_id

    assert patch(client, admin, complaint_id, {"assignedWorkerId": None}).json()["data"]["assignedWorker"] is None

    sync_db["users"].update_one({"email": "road@example.com"}, {"$set": {"isActive": False}})
    assert patch(client, admin, complaint_id, {"assignedWorkerId": road_id}).status_code == 404


# ---------- delete ----------

def test_admin_can_delete_a_complaint_and_everything_attached(client, create_user, sync_db):
    admin = make_admin(create_user)
    owner = create_user(email="owner@example.com")
    voter = create_user(email="voter@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, owner, sync_db)
    client.post(f"{COMPLAINTS_URL}/{complaint_id}/upvote", headers=voter)
    set_status(client, worker, complaint_id, "IN_PROGRESS")  # creates a notification for the owner
    stored = stored_complaint(sync_db, complaint_id)
    photo_path = os.path.join(settings.upload_dir, stored["photoUrl"].removeprefix("/uploads/"))
    assert os.path.exists(photo_path)

    response = client.delete(f"{COMPLAINTS_URL}/{complaint_id}", headers=admin)
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    assert stored_complaint(sync_db, complaint_id) is None
    assert sync_db["upvotes"].count_documents({"complaintId": ObjectId(complaint_id)}) == 0
    assert sync_db["notifications"].count_documents({"complaintId": ObjectId(complaint_id)}) == 0
    assert not os.path.exists(photo_path)
    entry = audit_entries(sync_db, "COMPLAINT_DELETED")[0]
    assert entry["metadata"]["complaintNumber"] == stored["complaintNumber"]
    assert entry["metadata"]["upvoteCount"] == 1

    assert client.delete(f"{COMPLAINTS_URL}/{complaint_id}", headers=admin).status_code == 404
    assert client.get(f"{COMPLAINTS_URL}/{complaint_id}", headers=owner).status_code == 404


# ---------- admin status override ----------

def test_admin_can_move_any_complaint_through_the_same_transitions(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db, code="GARBAGE")  # no worker exists at all
    url = f"{COMPLAINTS_URL}/{complaint_id}/status"

    assert client.patch(url, json={"status": "RESOLVED"}, headers=admin).status_code == 409  # cannot skip a step
    response = client.patch(url, json={"status": "IN_PROGRESS", "note": "Escalated by admin"}, headers=admin)
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "IN_PROGRESS"
    assert response.json()["data"]["assignedWorker"] is None  # an admin does not become the assigned worker
    assert client.patch(url, json={"status": "RESOLVED"}, headers=admin).status_code == 200

    notes = sync_db["notifications"].find({"type": "STATUS_CHANGED"})
    assert len(list(notes)) == 2
    assert [e["metadata"]["byRole"] for e in audit_entries(sync_db, "STATUS_CHANGED")] == ["ADMIN", "ADMIN"]
    assert client.patch(f"{COMPLAINTS_URL}/{ObjectId()}/status", json={"status": "IN_PROGRESS"}, headers=admin).status_code == 404


@pytest.mark.parametrize("method, suffix, body", [
    ("patch", "", {"priority": "LOW"}), ("delete", "", None), ("patch", "/status", {"status": "IN_PROGRESS"}),
])
def test_citizen_and_worker_cannot_use_admin_complaint_actions(client, create_user, sync_db, method, suffix, body):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)
    for headers in (citizen, worker):
        kwargs = {"json": body} if body is not None else {}
        response = getattr(client, method)(f"{COMPLAINTS_URL}/{complaint_id}{suffix}", headers=headers, **kwargs)
        assert response.status_code == 403
    assert stored_complaint(sync_db, complaint_id)["status"] == "SUBMITTED"
