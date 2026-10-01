CATEGORIES_URL = "/api/v1/categories"
DEPARTMENTS_URL = "/api/v1/departments"


def test_categories_require_login(client):
    assert client.get(CATEGORIES_URL).status_code == 401


def test_list_categories_returns_15_with_departments(client, create_user, seed_database):
    seed_database()
    headers = create_user()

    response = client.get(CATEGORIES_URL, headers=headers)
    categories = response.json()["data"]

    assert response.status_code == 200
    assert len(categories) == 15
    assert all(category["department"] is not None for category in categories)
    pothole = next(c for c in categories if c["code"] == "POTHOLE")
    assert pothole["department"]["code"] == "ROAD"


def test_get_category_by_id(client, create_user, seed_database):
    seed_database()
    headers = create_user()
    first = client.get(CATEGORIES_URL, headers=headers).json()["data"][0]

    response = client.get(f"{CATEGORIES_URL}/{first['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["name"] == first["name"]


def test_invalid_category_id_returns_400(client, create_user):
    headers = create_user()

    assert client.get(f"{CATEGORIES_URL}/not-an-id", headers=headers).status_code == 400


def test_unknown_category_id_returns_404(client, create_user):
    headers = create_user()

    response = client.get(f"{CATEGORIES_URL}/64b7f0000000000000000000", headers=headers)

    assert response.status_code == 404


def test_list_departments_returns_12(client, create_user, seed_database):
    seed_database()
    headers = create_user()

    response = client.get(DEPARTMENTS_URL, headers=headers)

    assert response.status_code == 200
    assert len(response.json()["data"]) == 12


def test_get_department_by_id(client, create_user, seed_database):
    seed_database()
    headers = create_user()
    first = client.get(DEPARTMENTS_URL, headers=headers).json()["data"][0]

    response = client.get(f"{DEPARTMENTS_URL}/{first['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["code"] == first["code"]


def test_inactive_category_is_hidden(client, create_user, seed_database, sync_db):
    seed_database()
    headers = create_user()
    sync_db["categories"].update_one({"code": "POTHOLE"}, {"$set": {"isActive": False}})

    categories = client.get(CATEGORIES_URL, headers=headers).json()["data"]

    assert len(categories) == 14