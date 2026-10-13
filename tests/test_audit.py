import pytest
from bson import ObjectId
from phase1011_support import (  # noqa: F401
    ADMIN_URL,
    audit_entries,
    clean_phase1011,
    department_id,
    make_admin,
    user_by_email,
)
from phase67_support import clean_notifications, make_complaint, make_worker, seeded, set_status  # noqa: F401
from phase89_support import clean_ledger  # noqa: F401

from app.services import audit_service


def logs(client, admin, query=""):
    return client.get(f"{ADMIN_URL}/audit-logs{query}", headers=admin).json()["data"]


def test_worker_status_change_is_audited_with_actor_and_details(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")

    data = logs(client, admin)
    assert data["total"] == 1
    entry = data["items"][0]
    assert entry["action"] == "STATUS_CHANGED" and entry["entity"] == "COMPLAINT"
    assert entry["entityId"] == complaint_id
    assert entry["user"] == {"id": str(user_by_email(sync_db, "worker@example.com")["_id"]), "name": "Test User", "role": "WORKER"}
    assert entry["metadata"]["from"] == "SUBMITTED" and entry["metadata"]["to"] == "IN_PROGRESS"
    assert entry["metadata"]["complaintNumber"].startswith("CIV-")


def test_rejected_actions_are_not_audited(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)
    set_status(client, worker, complaint_id, "RESOLVED")  # invalid jump: 409
    assert audit_entries(sync_db) == []


def test_filters_and_pagination(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")
    client.post(f"{ADMIN_URL}/workers", headers=admin, json={
        "name": "New Worker", "email": "new@example.com", "password": "Passw0rd123", "departmentId": department_id(sync_db, "ROAD")})

    assert logs(client, admin)["total"] == 3
    assert logs(client, admin, "?action=STATUS_CHANGED")["total"] == 2
    assert logs(client, admin, "?action=WORKER_CREATED")["total"] == 1
    assert logs(client, admin, "?entity=complaint")["total"] == 2
    assert logs(client, admin, "?entity=USER")["total"] == 1
    worker_id = str(user_by_email(sync_db, "worker@example.com")["_id"])
    assert logs(client, admin, f"?userId={worker_id}")["total"] == 2
    page = logs(client, admin, "?limit=2&page=2")
    assert page["total"] == 3 and len(page["items"]) == 1
    newest_first = [e["createdAt"] for e in logs(client, admin)["items"]]
    assert newest_first == sorted(newest_first, reverse=True)

    assert client.get(f"{ADMIN_URL}/audit-logs?action=NOPE", headers=admin).status_code == 422
    assert client.get(f"{ADMIN_URL}/audit-logs?userId=bad", headers=admin).status_code == 400
    assert client.get(f"{ADMIN_URL}/audit-logs?limit=101", headers=admin).status_code == 422


def test_audit_logs_are_admin_only(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    assert client.get(f"{ADMIN_URL}/audit-logs").status_code == 401
    assert client.get(f"{ADMIN_URL}/audit-logs", headers=citizen).status_code == 403
    assert client.get(f"{ADMIN_URL}/audit-logs", headers=worker).status_code == 403


def test_no_secrets_end_up_in_the_audit_log(client, create_user, sync_db):
    admin = make_admin(create_user)
    created = client.post(f"{ADMIN_URL}/workers", headers=admin, json={
        "name": "Secret Worker", "email": "secret@example.com", "password": "VerySecret123", "departmentId": department_id(sync_db, "ROAD")})
    worker_id = created.json()["data"]["id"]
    client.patch(f"{ADMIN_URL}/workers/{worker_id}", headers=admin, json={"password": "AnotherSecret456"})
    client.post("/api/v1/users/me/change-password", headers=admin, json={"currentPassword": "Passw0rd123", "newPassword": "BrandNew789"})

    text = str(audit_entries(sync_db)) + client.get(f"{ADMIN_URL}/audit-logs", headers=admin).text
    for secret in ("VerySecret123", "AnotherSecret456", "BrandNew789", "Passw0rd123", "secret@example.com", "$2b$", "passwordHash"):
        assert secret not in text


def test_a_failing_audit_write_never_breaks_the_action(client, create_user, sync_db, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(audit_service, "build_audit_document", broken)
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)

    response = set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "IN_PROGRESS"
    assert audit_entries(sync_db) == []


def test_metadata_values_are_made_safe():
    cleaned = audit_service._clean({"id": ObjectId(), "nested": {"ids": [ObjectId()]}, "weird": object(), "n": 1})
    assert isinstance(cleaned["id"], str)
    assert isinstance(cleaned["nested"]["ids"][0], str)
    assert isinstance(cleaned["weird"], str)
    assert cleaned["n"] == 1
