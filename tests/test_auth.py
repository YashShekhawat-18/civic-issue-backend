REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
ME_URL = "/api/v1/auth/me"


def valid_payload(**changes):
    payload = {
        "name": "Asha Patil",
        "email": "asha@example.com",
        "password": "Passw0rd123",
        "phone": "9876543210",
    }
    payload.update(changes)
    return payload


def test_register_success(client):
    response = client.post(REGISTER_URL, json=valid_payload())
    body = response.json()

    assert response.status_code == 201
    assert body["success"] is True
    assert body["data"]["email"] == "asha@example.com"
    assert body["data"]["role"] == "CITIZEN"
    assert "passwordHash" not in body["data"]
    assert "password" not in body["data"]


def test_register_rejects_role_in_body(client):
    response = client.post(REGISTER_URL, json=valid_payload(role="ADMIN"))

    assert response.status_code == 422
    assert response.json()["success"] is False


def test_register_duplicate_email(client):
    client.post(REGISTER_URL, json=valid_payload())
    response = client.post(REGISTER_URL, json=valid_payload(email="ASHA@Example.com"))

    assert response.status_code == 409


def test_register_weak_password(client):
    response = client.post(REGISTER_URL, json=valid_payload(password="short"))

    assert response.status_code == 422


def test_register_invalid_email(client):
    response = client.post(REGISTER_URL, json=valid_payload(email="not-an-email"))

    assert response.status_code == 422


def test_login_success(client):
    client.post(REGISTER_URL, json=valid_payload())
    response = client.post(LOGIN_URL, json={"email": "asha@example.com", "password": "Passw0rd123"})
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["tokenType"] == "bearer"
    assert body["data"]["accessToken"]


def test_login_wrong_password(client):
    client.post(REGISTER_URL, json=valid_payload())
    response = client.post(LOGIN_URL, json={"email": "asha@example.com", "password": "WrongPass999"})

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"


def test_login_unknown_email(client):
    response = client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "Passw0rd123"})

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"


def test_me_requires_token(client):
    response = client.get(ME_URL)

    assert response.status_code == 401


def test_me_rejects_invalid_token(client):
    response = client.get(ME_URL, headers={"Authorization": "Bearer this.is.not.valid"})

    assert response.status_code == 401


def test_me_returns_current_user(client, create_user):
    headers = create_user(email="me@example.com")
    response = client.get(ME_URL, headers=headers)

    assert response.status_code == 200
    assert response.json()["data"]["email"] == "me@example.com"


def test_deactivated_user_is_blocked(client, create_user, sync_db):
    headers = create_user(email="blocked@example.com")
    sync_db["users"].update_one({"email": "blocked@example.com"}, {"$set": {"isActive": False}})

    assert client.get(ME_URL, headers=headers).status_code == 401
    login = client.post(LOGIN_URL, json={"email": "blocked@example.com", "password": "Passw0rd123"})
    assert login.status_code == 403