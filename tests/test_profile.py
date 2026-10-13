import pytest
from phase1011_support import audit_entries, clean_phase1011, user_by_email  # noqa: F401
from phase67_support import clean_notifications, seeded  # noqa: F401
from phase89_support import clean_ledger  # noqa: F401

ME = "/api/v1/users/me"
PASSWORD = "Passw0rd123"


def test_update_own_name_and_phone(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    response = client.patch(ME, json={"name": "  New Name ", "phone": "9876543210"}, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "New Name" and data["phone"] == "9876543210"
    assert client.get("/api/v1/auth/me", headers=headers).json()["data"]["name"] == "New Name"
    assert audit_entries(sync_db, "PROFILE_UPDATED")[0]["metadata"]["fields"] == ["name", "phone"]

    assert client.patch(ME, json={"phone": None}, headers=headers).json()["data"]["phone"] is None


@pytest.mark.parametrize("body", [
    {}, {"name": "A"}, {"phone": "12"},
    {"role": "ADMIN"}, {"points": 9999}, {"isActive": False}, {"email": "x@example.com"}, {"badges": ["City Champion"]},
])
def test_profile_cannot_change_protected_fields(client, create_user, sync_db, body):
    headers = create_user(email="citizen@example.com")
    assert client.patch(ME, json=body, headers=headers).status_code == 422
    user = user_by_email(sync_db, "citizen@example.com")
    assert user["role"] == "CITIZEN" and user["points"] == 0 and user["badges"] == [] and user["isActive"] is True


def test_profile_needs_login(client):
    assert client.patch(ME, json={"name": "Someone"}).status_code == 401
    assert client.post(f"{ME}/change-password", json={"currentPassword": "a", "newPassword": "b"}).status_code == 401


def test_change_password(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    url = f"{ME}/change-password"
    new = "BrandNew123"

    response = client.post(url, json={"currentPassword": PASSWORD, "newPassword": new}, headers=headers)
    assert response.status_code == 200
    assert client.post("/api/v1/auth/login", json={"email": "citizen@example.com", "password": PASSWORD}).status_code == 401
    assert client.post("/api/v1/auth/login", json={"email": "citizen@example.com", "password": new}).status_code == 200
    assert audit_entries(sync_db, "PASSWORD_CHANGED")
    assert new not in str(audit_entries(sync_db))


def test_change_password_rules(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    url = f"{ME}/change-password"
    before = user_by_email(sync_db, "citizen@example.com")["passwordHash"]

    wrong = client.post(url, json={"currentPassword": "WrongPass123", "newPassword": "BrandNew123"}, headers=headers)
    assert wrong.status_code == 400 and "incorrect" in wrong.json()["message"]
    same = client.post(url, json={"currentPassword": PASSWORD, "newPassword": PASSWORD}, headers=headers)
    assert same.status_code == 422
    for weak in ("short1", "onlyletters", "12345678", "x" * 73 + "1"):
        assert client.post(url, json={"currentPassword": PASSWORD, "newPassword": weak}, headers=headers).status_code == 422
    assert client.post(url, json={"newPassword": "BrandNew123"}, headers=headers).status_code == 422
    assert client.post(url, json={"currentPassword": PASSWORD, "newPassword": "BrandNew123", "role": "ADMIN"}, headers=headers).status_code == 422
    assert user_by_email(sync_db, "citizen@example.com")["passwordHash"] == before
