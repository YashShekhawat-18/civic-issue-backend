from app.core.config import settings


def test_seed_creates_expected_records(seed_database, sync_db):
    seed_database()

    assert sync_db["departments"].count_documents({}) == 12
    assert sync_db["categories"].count_documents({}) == 15
    assert sync_db["badges"].count_documents({}) == 4
    assert sync_db["users"].count_documents({"role": "ADMIN"}) == 1
    assert sync_db["users"].count_documents({"role": "WORKER"}) == 4


def test_categories_link_to_the_right_departments(seed_database, sync_db):
    seed_database()
    expected = {
        "POTHOLE": "ROAD",
        "ROAD_DAMAGE": "ROAD",
        "ILLEGAL_PARKING": "TRAFFIC",
        "TRAFFIC_SIGNAL": "TRAFFIC",
        "TREE_FALLEN_BRANCH": "GARDEN",
        "NOISE_COMPLAINT": "ENVIRONMENT",
        "OTHER": "GENERAL",
    }

    for category_code, department_code in expected.items():
        category = sync_db["categories"].find_one({"code": category_code})
        department = sync_db["departments"].find_one({"_id": category["departmentId"]})
        assert department["code"] == department_code


def test_running_seed_twice_creates_no_duplicates(seed_database, sync_db):
    seed_database()
    seed_database()

    assert sync_db["departments"].count_documents({}) == 12
    assert sync_db["categories"].count_documents({}) == 15
    assert sync_db["badges"].count_documents({}) == 4
    assert sync_db["users"].count_documents({}) == 5


def test_rerunning_seed_keeps_admin_edits(seed_database, sync_db):
    seed_database()
    sync_db["departments"].update_one({"code": "ROAD"}, {"$set": {"description": "Edited by admin"}})

    seed_database()

    assert sync_db["departments"].find_one({"code": "ROAD"})["description"] == "Edited by admin"


def test_workers_have_departments_and_admin_does_not(seed_database, sync_db):
    seed_database()

    workers = list(sync_db["users"].find({"role": "WORKER"}))
    assert all(worker["departmentId"] is not None for worker in workers)
    assert sync_db["users"].find_one({"role": "ADMIN"})["departmentId"] is None


def test_seeded_admin_can_log_in(client, seed_database):
    seed_database()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": settings.seed_admin_email, "password": settings.seed_admin_password},
    )

    assert response.status_code == 200
    assert response.json()["data"]["user"]["role"] == "ADMIN"