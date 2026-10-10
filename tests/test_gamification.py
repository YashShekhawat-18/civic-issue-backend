import asyncio

from bson import ObjectId
from phase67_support import (  # noqa: F401  (the fixtures must be imported to be active)
    NOTIFICATIONS_URL,
    clean_notifications,
    make_complaint,
    make_worker,
    seeded,
    set_status,
)
from phase89_support import (  # noqa: F401
    GAMIFICATION_URL,
    clean_ledger,
    run_with_db,
    seed_badges,
    user_doc,
)
from civic_test_helpers import complaint_form, post_complaint

from app.core.config import settings
from app.models.points_ledger import PointsEvent
from app.services import gamification_service


def points_of(sync_db, email):
    return user_doc(sync_db, email)["points"]


def badges_of(sync_db, email):
    return user_doc(sync_db, email)["badges"]


def upvote(client, headers, complaint_id):
    return client.post(f"/api/v1/complaints/{complaint_id}/upvote", headers=headers)


# ---------- earning points ----------

def test_new_complaint_gives_points_and_the_first_badge(client, create_user, sync_db):
    seed_badges(sync_db)
    citizen = create_user(email="citizen@example.com")
    make_complaint(client, citizen, sync_db)

    assert points_of(sync_db, "citizen@example.com") == 10
    assert badges_of(sync_db, "citizen@example.com") == ["Newcomer"]
    assert sync_db["points_ledger"].count_documents({"event": "COMPLAINT_CREATED"}) == 1

    notes = client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["items"]
    assert [n["type"] for n in notes] == ["BADGE_EARNED"]
    assert "Newcomer" in notes[0]["title"]
    assert notes[0]["complaintId"] is None


def test_duplicate_complaint_earns_nothing(client, create_user, sync_db):
    first = create_user(email="first@example.com")
    second = create_user(email="second@example.com")
    make_complaint(client, first, sync_db)
    response = post_complaint(client, second, complaint_form(sync_db))
    assert response.status_code == 200 and response.json()["data"]["duplicate"] is True
    assert points_of(sync_db, "second@example.com") == 0


def test_rejected_complaint_earns_nothing(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    response = post_complaint(client, citizen, complaint_form(sync_db), content=b"not an image", filename="a.png")
    assert response.status_code >= 400
    assert points_of(sync_db, "citizen@example.com") == 0


def test_upvote_gives_points_once_per_complaint(client, create_user, sync_db):
    owner = create_user(email="owner@example.com")
    voter = create_user(email="voter@example.com")
    complaint_id = make_complaint(client, owner, sync_db)

    assert upvote(client, voter, complaint_id).status_code == 201
    assert points_of(sync_db, "voter@example.com") == 2
    assert points_of(sync_db, "owner@example.com") == 10  # the reporter gets nothing extra

    # Farming attempts: upvote again, remove and upvote again
    assert upvote(client, voter, complaint_id).status_code == 409
    client.delete(f"/api/v1/complaints/{complaint_id}/upvote", headers=voter)
    assert upvote(client, voter, complaint_id).status_code == 201
    assert points_of(sync_db, "voter@example.com") == 2


def test_removing_an_upvote_keeps_the_points(client, create_user, sync_db):
    owner = create_user(email="owner@example.com")
    voter = create_user(email="voter@example.com")
    complaint_id = make_complaint(client, owner, sync_db)
    upvote(client, voter, complaint_id)
    client.delete(f"/api/v1/complaints/{complaint_id}/upvote", headers=voter)
    assert points_of(sync_db, "voter@example.com") == 2


def test_own_complaint_upvote_is_refused_and_earns_nothing(client, create_user, sync_db):
    owner = create_user(email="owner@example.com")
    complaint_id = make_complaint(client, owner, sync_db)
    assert upvote(client, owner, complaint_id).status_code == 403
    assert points_of(sync_db, "owner@example.com") == 10


def test_resolved_complaint_rewards_the_reporter_once(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)

    set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert points_of(sync_db, "citizen@example.com") == 10  # nothing yet
    assert set_status(client, worker, complaint_id, "RESOLVED").status_code == 200
    assert points_of(sync_db, "citizen@example.com") == 30
    assert set_status(client, worker, complaint_id, "RESOLVED").status_code == 409  # rejected
    assert points_of(sync_db, "citizen@example.com") == 30
    assert points_of(sync_db, "worker@example.com") == 0


def test_anonymous_reporter_still_earns_points(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    make_complaint(client, citizen, sync_db, isAnonymous="true")
    assert points_of(sync_db, "citizen@example.com") == 10


# ---------- rules: ledger, badges, settings ----------

def award(sync_db, email, event=PointsEvent.COMPLAINT_CREATED, complaint_id=None):
    user_id = user_doc(sync_db, email)["_id"]
    complaint_id = complaint_id or ObjectId()
    return run_with_db(
        lambda db: gamification_service.award_points(user_id=user_id, event=event, complaint_id=complaint_id, db=db)
    )


def test_same_event_on_same_complaint_pays_only_once(client, create_user, sync_db):
    create_user(email="citizen@example.com")
    complaint_id = ObjectId()
    assert award(sync_db, "citizen@example.com", complaint_id=complaint_id)["pointsAdded"] == 10
    assert award(sync_db, "citizen@example.com", complaint_id=complaint_id) is None
    assert points_of(sync_db, "citizen@example.com") == 10
    # a different complaint is a different reward
    assert award(sync_db, "citizen@example.com")["totalPoints"] == 20


def test_two_awards_at_the_same_time_pay_once(client, create_user, sync_db):
    create_user(email="citizen@example.com")
    user_id = user_doc(sync_db, "citizen@example.com")["_id"]
    complaint_id = ObjectId()

    async def both(db):
        return await asyncio.gather(
            *[
                gamification_service.award_points(
                    user_id=user_id, event=PointsEvent.COMPLAINT_CREATED, complaint_id=complaint_id, db=db
                )
                for _ in range(2)
            ]
        )

    results = run_with_db(both)
    assert [r is not None for r in results].count(True) == 1
    assert points_of(sync_db, "citizen@example.com") == 10


def test_badges_are_given_at_their_thresholds_and_only_once(client, create_user, sync_db):
    seed_badges(sync_db)
    create_user(email="citizen@example.com")
    sync_db["users"].update_one({"email": "citizen@example.com"}, {"$set": {"points": 45}})

    result = award(sync_db, "citizen@example.com")  # 45 + 10 = 55
    assert result["totalPoints"] == 55
    assert result["newBadges"] == ["Newcomer", "Active Citizen"]  # catches up on everything reached
    assert award(sync_db, "citizen@example.com")["newBadges"] == []
    assert badges_of(sync_db, "citizen@example.com") == ["Newcomer", "Active Citizen"]
    assert sync_db["notifications"].count_documents({"type": "BADGE_EARNED"}) == 2


def test_badge_is_not_given_twice_when_two_requests_race(client, create_user, sync_db):
    seed_badges(sync_db)
    create_user(email="citizen@example.com")
    sync_db["users"].update_one({"email": "citizen@example.com"}, {"$set": {"points": 20}})
    stale_user = user_doc(sync_db, "citizen@example.com")  # both "requests" saw badges == []

    async def both(db):
        first = await gamification_service._award_badges(db, stale_user)
        second = await gamification_service._award_badges(db, stale_user)
        return first, second

    first, second = run_with_db(both)
    assert first == ["Newcomer"]
    assert second == []  # the atomic update refused the repeat
    assert badges_of(sync_db, "citizen@example.com") == ["Newcomer"]
    assert sync_db["notifications"].count_documents({"type": "BADGE_EARNED"}) == 1


def test_inactive_badge_is_not_awarded(client, create_user, sync_db):
    seed_badges(sync_db)
    sync_db["badges"].update_one({"name": "Newcomer"}, {"$set": {"isActive": False}})
    create_user(email="citizen@example.com")
    assert award(sync_db, "citizen@example.com")["newBadges"] == []


def test_point_values_come_from_settings_and_zero_switches_off(client, create_user, sync_db, monkeypatch):
    create_user(email="citizen@example.com")
    monkeypatch.setattr(settings, "points_complaint_created", 25)
    assert award(sync_db, "citizen@example.com")["pointsAdded"] == 25
    monkeypatch.setattr(settings, "points_complaint_created", 0)
    assert award(sync_db, "citizen@example.com") is None
    assert points_of(sync_db, "citizen@example.com") == 25
    assert sync_db["points_ledger"].count_documents({}) == 1


def test_failure_in_points_does_not_break_the_complaint(client, create_user, sync_db, monkeypatch):
    async def broken(*args, **kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(gamification_service, "_award_points", broken)
    citizen = create_user(email="citizen@example.com")
    response = post_complaint(client, citizen, complaint_form(sync_db))
    assert response.status_code == 201
    assert points_of(sync_db, "citizen@example.com") == 0


# ---------- endpoints ----------

def test_gamification_endpoints_need_login(client):
    for path in ("/me", "/badges", "/leaderboard"):
        assert client.get(f"{GAMIFICATION_URL}{path}").status_code == 401


def test_my_summary_shows_points_badges_next_badge_and_activity(client, create_user, sync_db):
    seed_badges(sync_db)
    citizen = create_user(email="citizen@example.com")
    worker = make_worker(create_user, sync_db)
    complaint_id = make_complaint(client, citizen, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")

    data = client.get(f"{GAMIFICATION_URL}/me", headers=citizen).json()["data"]
    assert data["points"] == 30
    assert [b["name"] for b in data["badges"]] == ["Newcomer"]
    assert data["nextBadge"]["name"] == "Active Citizen"
    assert data["nextBadge"]["pointsNeeded"] == 20
    assert [a["event"] for a in data["recentActivity"]] == ["COMPLAINT_RESOLVED", "COMPLAINT_CREATED"]
    assert data["recentActivity"][0]["complaintId"] == complaint_id


def test_summary_for_a_new_user_and_when_all_badges_are_earned(client, create_user, sync_db):
    seed_badges(sync_db)
    citizen = create_user(email="citizen@example.com")
    data = client.get(f"{GAMIFICATION_URL}/me", headers=citizen).json()["data"]
    assert data["points"] == 0 and data["badges"] == [] and data["recentActivity"] == []
    assert data["nextBadge"]["name"] == "Newcomer"

    sync_db["users"].update_one(
        {"email": "citizen@example.com"},
        {"$set": {"points": 900, "badges": ["Newcomer", "Active Citizen", "Community Helper", "City Champion"]}},
    )
    data = client.get(f"{GAMIFICATION_URL}/me", headers=citizen).json()["data"]
    assert data["nextBadge"] is None
    assert len(data["badges"]) == 4


def test_badge_list_is_sorted_and_hides_inactive(client, create_user, sync_db):
    seed_badges(sync_db)
    sync_db["badges"].update_one({"name": "City Champion"}, {"$set": {"isActive": False}})
    citizen = create_user(email="citizen@example.com")
    data = client.get(f"{GAMIFICATION_URL}/badges", headers=citizen).json()["data"]
    assert [b["pointsRequired"] for b in data] == [10, 50, 150]


def test_leaderboard_shows_only_active_citizens_and_no_private_data(client, create_user, sync_db):
    top = create_user(email="top@example.com")
    create_user(email="middle@example.com")
    create_user(email="zero@example.com")
    create_user(email="gone@example.com")
    create_user(email="worker@example.com", role="WORKER")
    for email, name, points in (("top@example.com", "Top Citizen", 90), ("middle@example.com", "Middle", 40),
                                ("gone@example.com", "Gone", 500), ("worker@example.com", "Worker", 999)):
        sync_db["users"].update_one({"email": email}, {"$set": {"name": name, "points": points}})
    sync_db["users"].update_one({"email": "gone@example.com"}, {"$set": {"isActive": False}})

    response = client.get(f"{GAMIFICATION_URL}/leaderboard", headers=top)
    data = response.json()["data"]
    assert [(r["rank"], r["name"], r["points"]) for r in data] == [(1, "Top Citizen", 90), (2, "Middle", 40)]
    assert "@example.com" not in response.text
    assert set(data[0]) == {"rank", "name", "points", "badgeCount"}

    assert len(client.get(f"{GAMIFICATION_URL}/leaderboard?limit=1", headers=top).json()["data"]) == 1
    assert client.get(f"{GAMIFICATION_URL}/leaderboard?limit=0", headers=top).status_code == 422
    assert client.get(f"{GAMIFICATION_URL}/leaderboard?limit=51", headers=top).status_code == 422
