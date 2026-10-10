import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from phase67_support import (  # noqa: F401  (the fixtures must be imported to be active)
    NOTIFICATIONS_URL,
    clean_notifications,
    make_complaint,
    make_worker,
    seeded,
    set_status,
)
from phase89_support import OVERDUE_URL, clean_ledger, make_old, run_with_db  # noqa: F401

from app.core.config import settings
from app.jobs import scheduler as scheduler_module
from app.services import overdue_service


def run_check(**kwargs):
    return run_with_db(lambda db: overdue_service.mark_overdue_complaints(db, **kwargs))


def flag(sync_db, complaint_id):
    return sync_db["complaints"].find_one({"_id": ObjectId(complaint_id)})["overdue"]


def overdue_notifications(sync_db):
    return list(sync_db["notifications"].find({"type": "COMPLAINT_OVERDUE"}))


# ---------- the rule ----------

def test_old_unresolved_complaint_becomes_overdue(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    submitted = make_complaint(client, citizen, sync_db, spot=0)
    in_progress = make_complaint(client, citizen, sync_db, spot=1)
    make_worker(create_user, sync_db)
    set_status(client, make_worker(create_user, sync_db, "w2@example.com"), in_progress, "IN_PROGRESS")
    make_old(sync_db, submitted, 4)
    make_old(sync_db, in_progress, 4)

    result = run_check()
    assert result == {"checked": 2, "markedOverdue": 2}
    assert flag(sync_db, submitted) is True
    assert flag(sync_db, in_progress) is True


def test_recent_complaint_is_not_overdue(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    recent = make_complaint(client, citizen, sync_db, spot=0)
    almost = make_complaint(client, citizen, sync_db, spot=1)
    sync_db["complaints"].update_one(
        {"_id": ObjectId(almost)},
        {"$set": {"createdAt": datetime.now(timezone.utc) - timedelta(days=3) + timedelta(minutes=5)}},
    )
    assert run_check() == {"checked": 0, "markedOverdue": 0}
    assert flag(sync_db, recent) is False
    assert flag(sync_db, almost) is False  # 5 minutes short of 3 days


def test_resolved_complaint_is_never_overdue(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")
    make_old(sync_db, complaint_id, 10)

    assert run_check()["markedOverdue"] == 0
    assert flag(sync_db, complaint_id) is False


def test_overdue_days_setting_is_respected(client, create_user, sync_db, monkeypatch):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    make_old(sync_db, complaint_id, 2)

    assert run_check()["markedOverdue"] == 0  # 3 days by default
    monkeypatch.setattr(settings, "overdue_days", 1)
    assert run_check()["markedOverdue"] == 1


def test_running_twice_marks_and_notifies_only_once(client, create_user, sync_db):
    admin = create_user(email="admin@example.com", role="ADMIN")
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    make_old(sync_db, complaint_id, 5)

    assert run_check()["markedOverdue"] == 1
    assert run_check() == {"checked": 0, "markedOverdue": 0}
    assert len(overdue_notifications(sync_db)) == 1


def test_two_checks_started_together_notify_once(client, create_user, sync_db):
    create_user(email="admin@example.com", role="ADMIN")
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    make_old(sync_db, complaint_id, 5)

    async def both(db):
        return await asyncio.gather(
            overdue_service.mark_overdue_complaints(db), overdue_service.mark_overdue_complaints(db)
        )

    results = run_with_db(both)
    assert sum(r["markedOverdue"] for r in results) == 1
    assert len(overdue_notifications(sync_db)) == 1


# ---------- who is told ----------

def test_every_active_admin_is_notified_and_nobody_else(client, create_user, sync_db):
    admin_one = create_user(email="admin1@example.com", role="ADMIN")
    admin_two = create_user(email="admin2@example.com", role="ADMIN")
    create_user(email="gone@example.com", role="ADMIN")
    sync_db["users"].update_one({"email": "gone@example.com"}, {"$set": {"isActive": False}})
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db, title="Pothole on the main road")
    make_old(sync_db, complaint_id, 4)
    run_check()

    for headers in (admin_one, admin_two):
        data = client.get(NOTIFICATIONS_URL, headers=headers).json()["data"]
        assert data["total"] == 1
        item = data["items"][0]
        assert item["type"] == "COMPLAINT_OVERDUE"
        assert item["complaintId"] == complaint_id
        assert "CIV-" in item["message"]
        assert "Pothole on the main road" in item["message"]
        assert "Road" in item["message"]
    assert len(overdue_notifications(sync_db)) == 2  # the deactivated admin got nothing
    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["total"] == 0
    assert client.get(NOTIFICATIONS_URL, headers=worker).json()["data"]["total"] == 0


def test_stale_candidate_list_cannot_cause_a_second_mark(client, create_user, sync_db):
    """Simulates two job copies: the second one read its list BEFORE the first one finished."""
    create_user(email="admin@example.com", role="ADMIN")
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    make_old(sync_db, complaint_id, 5)
    stale = [sync_db["complaints"].find_one({"_id": ObjectId(complaint_id)})]  # overdue is still False here
    assert run_check()["markedOverdue"] == 1

    class StaleCursor:
        def sort(self, *args):
            return self

        def limit(self, *args):
            return self

        async def to_list(self, *args):
            return stale

    class StaleComplaints:
        def __init__(self, real):
            self._real = real

        def find(self, *args, **kwargs):
            return StaleCursor()

        def __getattr__(self, name):
            return getattr(self._real, name)

    class StaleDb:
        def __init__(self, real):
            self._real = real

        def __getitem__(self, name):
            return StaleComplaints(self._real[name]) if name == "complaints" else self._real[name]

    result = run_with_db(lambda db: overdue_service.mark_overdue_complaints(StaleDb(db)))
    assert result == {"checked": 1, "markedOverdue": 0}  # the atomic update refused it
    assert len(overdue_notifications(sync_db)) == 1


def test_check_works_when_there_is_no_admin(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    make_old(sync_db, complaint_id, 4)
    assert run_check()["markedOverdue"] == 1
    assert overdue_notifications(sync_db) == []


# ---------- admin routes ----------

def test_overdue_routes_are_admin_only(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    for method, url in (("get", OVERDUE_URL), ("post", f"{OVERDUE_URL}/check")):
        assert getattr(client, method)(url).status_code == 401
        assert getattr(client, method)(url, headers=citizen).status_code == 403
        assert getattr(client, method)(url, headers=worker).status_code == 403


def test_admin_can_run_the_check_and_list_overdue(client, create_user, sync_db):
    admin = create_user(email="admin@example.com", role="ADMIN")
    citizen = create_user(email="citizen@example.com")
    older = make_complaint(client, citizen, sync_db, spot=0)
    newer = make_complaint(client, citizen, sync_db, spot=1)
    fresh = make_complaint(client, citizen, sync_db, spot=2)
    make_old(sync_db, older, 9)
    make_old(sync_db, newer, 4)

    assert client.get(OVERDUE_URL, headers=admin).json()["data"]["total"] == 0  # not checked yet

    response = client.post(f"{OVERDUE_URL}/check", headers=admin)
    assert response.status_code == 200
    assert response.json()["data"] == {"checked": 2, "markedOverdue": 2}

    data = client.get(OVERDUE_URL, headers=admin).json()["data"]
    assert data["total"] == 2
    assert [item["id"] for item in data["items"]] == [older, newer]  # oldest first
    assert data["items"][0]["ageDays"] == 9
    assert data["items"][0]["department"]["code"] == "ROAD"
    assert fresh not in [item["id"] for item in data["items"]]

    page = client.get(f"{OVERDUE_URL}?limit=1&page=2", headers=admin).json()["data"]
    assert [item["id"] for item in page["items"]] == [newer]
    assert client.get(f"{OVERDUE_URL}?limit=0", headers=admin).status_code == 422


def test_overdue_list_drops_complaints_once_resolved(client, create_user, sync_db):
    admin = create_user(email="admin@example.com", role="ADMIN")
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)
    make_old(sync_db, complaint_id, 5)
    run_check()
    assert client.get(OVERDUE_URL, headers=admin).json()["data"]["total"] == 1

    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")
    assert client.get(OVERDUE_URL, headers=admin).json()["data"]["total"] == 0
    assert flag(sync_db, complaint_id) is True  # the history of being late is kept


# ---------- the scheduler ----------

def test_scheduler_is_built_with_the_overdue_job(monkeypatch):
    monkeypatch.setattr(settings, "overdue_check_minutes", 15)
    built = scheduler_module.build_scheduler()
    job = built.get_job(scheduler_module.OVERDUE_JOB_ID)
    assert job is not None
    assert job.trigger.interval == timedelta(minutes=15)
    assert job.max_instances == 1


def test_scheduler_does_not_start_in_tests_or_when_switched_off(monkeypatch):
    scheduler_module.start_scheduler()
    assert scheduler_module.scheduler is None  # APP_ENV=test

    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "scheduler_enabled", False)
    scheduler_module.start_scheduler()
    assert scheduler_module.scheduler is None


def test_a_crashing_job_is_logged_not_raised(monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("database down")

    monkeypatch.setattr(overdue_service, "mark_overdue_complaints", broken)
    asyncio.run(scheduler_module.run_overdue_check())  # must not raise


def test_empty_overdue_settings_in_env_use_defaults(tmp_path, monkeypatch):
    from app.core.config import Settings

    env_file = tmp_path / ".env"
    env_file.write_text("OVERDUE_DAYS=\nOVERDUE_CHECK_MINUTES=\nSCHEDULER_ENABLED=\n")
    for name in ("OVERDUE_DAYS", "OVERDUE_CHECK_MINUTES", "SCHEDULER_ENABLED"):
        monkeypatch.delenv(name, raising=False)
    loaded = Settings(_env_file=str(env_file))
    assert (loaded.overdue_days, loaded.overdue_check_minutes, loaded.scheduler_enabled) == (3, 60, True)


def test_invalid_overdue_settings_are_rejected():
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError):
        Settings(overdue_days=0)
    with pytest.raises(ValidationError):
        Settings(overdue_check_minutes=0)
