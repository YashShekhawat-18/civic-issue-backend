from phase1011_support import ADMIN_URL, clean_phase1011, make_admin  # noqa: F401
from phase67_support import clean_notifications, make_complaint, make_worker, seeded, set_status  # noqa: F401
from phase89_support import clean_ledger, make_old, run_with_db  # noqa: F401

from app.services import overdue_service


def build_data(client, create_user, sync_db):
    """5 complaints: 3 road (1 resolved, 1 in progress), 1 sanitation (overdue), 1 streetlight."""
    citizen = create_user(email="citizen@example.com")
    road_worker = make_worker(create_user, sync_db, "road@example.com", "ROAD")
    ids = {
        "pothole_resolved": make_complaint(client, citizen, sync_db, code="POTHOLE", spot=0),
        "pothole_progress": make_complaint(client, citizen, sync_db, code="POTHOLE", spot=1),
        "road_damage": make_complaint(client, citizen, sync_db, code="ROAD_DAMAGE", spot=2),
        "garbage": make_complaint(client, citizen, sync_db, code="GARBAGE", spot=3),
        "light": make_complaint(client, citizen, sync_db, code="STREETLIGHT", spot=4),
    }
    set_status(client, road_worker, ids["pothole_resolved"], "IN_PROGRESS")
    set_status(client, road_worker, ids["pothole_resolved"], "RESOLVED")
    set_status(client, road_worker, ids["pothole_progress"], "IN_PROGRESS")
    make_old(sync_db, ids["garbage"], 6)
    run_with_db(lambda db: overdue_service.mark_overdue_complaints(db))
    return ids


def test_statistics_are_correct(client, create_user, sync_db):
    admin = make_admin(create_user)
    ids = build_data(client, create_user, sync_db)

    data = client.get(f"{ADMIN_URL}/statistics", headers=admin).json()["data"]
    assert data["totals"] == {"total": 5, "submitted": 3, "inProgress": 1, "resolved": 1, "overdue": 1}
    assert data["resolutionRatePercent"] == 20.0
    assert data["byStatus"] == [
        {"status": "SUBMITTED", "count": 3}, {"status": "IN_PROGRESS", "count": 1}, {"status": "RESOLVED", "count": 1},
    ]
    by_category = {row["code"]: row["count"] for row in data["byCategory"]}
    assert by_category == {"POTHOLE": 2, "ROAD_DAMAGE": 1, "GARBAGE": 1, "STREETLIGHT": 1}
    assert data["byCategory"][0]["code"] == "POTHOLE"  # biggest first
    by_department = {row["code"]: row["count"] for row in data["byDepartment"]}
    assert by_department == {"ROAD": 3, "SANITATION": 1, "ELECTRICAL": 1}
    assert len(data["recentComplaints"]) == 5
    assert data["recentComplaints"][0]["id"] == ids["light"]  # newest first


def test_overdue_total_ignores_resolved_complaints(client, create_user, sync_db):
    admin = make_admin(create_user)
    ids = build_data(client, create_user, sync_db)
    worker = make_worker(create_user, sync_db, "sanitation@example.com", "SANITATION")
    set_status(client, worker, ids["garbage"], "IN_PROGRESS")
    set_status(client, worker, ids["garbage"], "RESOLVED")
    data = client.get(f"{ADMIN_URL}/statistics", headers=admin).json()["data"]
    assert data["totals"]["overdue"] == 0
    assert data["totals"]["resolved"] == 2


def test_recent_complaints_are_limited_to_ten(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    for spot in range(12):
        make_complaint(client, citizen, sync_db, spot=spot)
    data = client.get(f"{ADMIN_URL}/statistics", headers=admin).json()["data"]
    assert data["totals"]["total"] == 12
    assert len(data["recentComplaints"]) == 10


def test_statistics_on_an_empty_database(client, create_user, sync_db):
    admin = make_admin(create_user)
    data = client.get(f"{ADMIN_URL}/statistics", headers=admin).json()["data"]
    assert data["totals"] == {"total": 0, "submitted": 0, "inProgress": 0, "resolved": 0, "overdue": 0}
    assert data["resolutionRatePercent"] == 0.0
    assert data["byCategory"] == [] and data["byDepartment"] == [] and data["recentComplaints"] == []
    assert len(data["byStatus"]) == 3


def test_dashboard_contains_statistics_and_the_oldest_overdue(client, create_user, sync_db):
    admin = make_admin(create_user)
    ids = build_data(client, create_user, sync_db)
    data = client.get(f"{ADMIN_URL}/dashboard", headers=admin).json()["data"]
    assert data["totals"]["total"] == 5
    assert [c["id"] for c in data["oldestOverdue"]] == [ids["garbage"]]
    assert data["oldestOverdue"][0]["ageDays"] == 6


def test_dashboard_never_leaks_reporter_of_anonymous_complaint(client, create_user, sync_db):
    admin = make_admin(create_user)
    citizen = create_user(email="citizen@example.com")
    make_complaint(client, citizen, sync_db, isAnonymous="true")
    response = client.get(f"{ADMIN_URL}/dashboard", headers=admin)
    assert response.json()["data"]["recentComplaints"][0]["reporter"] is None
    assert "citizen@example.com" not in response.text
