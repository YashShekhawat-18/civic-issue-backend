from bson import ObjectId
from phase67_support import (  # noqa: F401  (the fixtures must be imported to be active)
    NOTIFICATIONS_URL,
    clean_notifications,
    make_complaint,
    make_worker,
    seeded,
    set_status,
)


def test_notifications_need_login(client):
    assert client.get(NOTIFICATIONS_URL).status_code == 401
    assert client.patch(f"{NOTIFICATIONS_URL}/read-all").status_code == 401


def test_citizen_is_notified_when_work_starts_and_when_resolved(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)

    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["total"] == 0

    set_status(client, worker, complaint_id, "IN_PROGRESS", note="Team is on the way")
    set_status(client, worker, complaint_id, "RESOLVED")

    data = client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]
    assert data["total"] == 2
    assert data["unreadCount"] == 2
    newest, oldest = data["items"]  # newest first
    assert newest["type"] == "STATUS_CHANGED"
    assert newest["title"] == "Your complaint has been resolved"
    assert newest["complaintId"] == complaint_id
    assert newest["isRead"] is False
    assert oldest["title"] == "Work has started on your complaint"
    assert "Road department" in oldest["message"]
    assert "Team is on the way" in oldest["message"]
    assert "CIV-" in oldest["message"]


def test_only_the_reporter_is_notified(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    other = create_user(email="other@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")

    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["total"] == 1
    assert client.get(NOTIFICATIONS_URL, headers=other).json()["data"]["total"] == 0
    assert client.get(NOTIFICATIONS_URL, headers=worker).json()["data"]["total"] == 0


def test_anonymous_reporter_is_still_notified(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db, isAnonymous="true")
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["total"] == 1


def test_mark_one_notification_as_read(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")

    items = client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["items"]
    response = client.patch(f"{NOTIFICATIONS_URL}/{items[0]['id']}/read", headers=citizen)
    assert response.status_code == 200
    assert response.json()["data"]["isRead"] is True

    data = client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]
    assert data["unreadCount"] == 1
    unread = client.get(f"{NOTIFICATIONS_URL}?unreadOnly=true", headers=citizen).json()["data"]
    assert unread["total"] == 1
    assert unread["items"][0]["id"] == items[1]["id"]

    # Marking it again is harmless
    assert client.patch(f"{NOTIFICATIONS_URL}/{items[0]['id']}/read", headers=citizen).status_code == 200


def test_cannot_mark_someone_elses_notification(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    other = create_user(email="other@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    notification_id = client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["items"][0]["id"]

    assert client.patch(f"{NOTIFICATIONS_URL}/{notification_id}/read", headers=other).status_code == 404
    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["unreadCount"] == 1  # still unread


def test_invalid_and_unknown_notification_ids(client, create_user):
    citizen = create_user(email="citizen@example.com")
    assert client.patch(f"{NOTIFICATIONS_URL}/not-an-id/read", headers=citizen).status_code == 400
    assert client.patch(f"{NOTIFICATIONS_URL}/{ObjectId()}/read", headers=citizen).status_code == 404


def test_mark_all_as_read_only_touches_my_notifications(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    other = create_user(email="other@example.com")
    worker = make_worker(create_user, sync_db)
    mine = make_complaint(client, citizen, sync_db, spot=0)
    theirs = make_complaint(client, other, sync_db, spot=1)
    for complaint_id in (mine, theirs):
        set_status(client, worker, complaint_id, "IN_PROGRESS")

    response = client.patch(f"{NOTIFICATIONS_URL}/read-all", headers=citizen)
    assert response.status_code == 200
    assert response.json()["data"]["updated"] == 1
    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["unreadCount"] == 0
    assert client.get(NOTIFICATIONS_URL, headers=other).json()["data"]["unreadCount"] == 1


def test_notification_list_pagination_and_validation(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    for spot in range(3):
        set_status(client, worker, make_complaint(client, citizen, sync_db, spot=spot), "IN_PROGRESS")

    page = client.get(f"{NOTIFICATIONS_URL}?limit=2&page=2", headers=citizen).json()["data"]
    assert page["total"] == 3
    assert len(page["items"]) == 1
    assert client.get(f"{NOTIFICATIONS_URL}?limit=0", headers=citizen).status_code == 422
    assert client.get(f"{NOTIFICATIONS_URL}?page=0", headers=citizen).status_code == 422


def test_notification_failure_does_not_break_the_status_change(client, create_user, sync_db, monkeypatch):
    from app.services import notification_service

    async def broken(*args, **kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(notification_service, "create_notification", broken)

    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    response = set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "IN_PROGRESS"
