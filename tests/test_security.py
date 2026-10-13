import re
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from bson import ObjectId
from civic_test_helpers import PNG_BYTES, complaint_form, post_complaint
from fastapi.testclient import TestClient
from phase1011_support import clean_phase1011, user_by_email  # noqa: F401
from phase67_support import clean_notifications, make_complaint, seeded  # noqa: F401
from phase89_support import clean_ledger  # noqa: F401

from app.core.config import settings, validate_settings
from app.core.rate_limit import SlidingWindowLimiter, limiter
from app.main import app

HEALTH = "/api/v1/health"
LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
PASSWORD = "Passw0rd123"


@pytest.fixture(autouse=True)
def fresh_limiter():
    limiter.reset()
    yield
    limiter.reset()


@pytest.fixture
def limits_on(monkeypatch):
    """The limiter is switched off while APP_ENV=test. These tests switch it on."""
    monkeypatch.setattr(settings, "app_env", "development")


def bad_login(client, email="nobody@example.com", **headers):
    return client.post(LOGIN, json={"email": email, "password": "WrongPass123"}, headers=headers)


# ---------- security headers ----------

def test_api_responses_carry_security_headers(client):
    response = client.get(HEALTH)
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert "geolocation=()" in response.headers["permissions-policy"]
    assert response.headers["cross-origin-opener-policy"] == "same-origin"
    assert response.headers["cache-control"] == "no-store"
    assert "default-src 'none'" in response.headers["content-security-policy"]
    assert "strict-transport-security" not in response.headers  # plain http


def test_hsts_only_over_https(client):
    response = client.get("https://testserver" + HEALTH)
    assert "max-age=" in response.headers["strict-transport-security"]


def test_error_responses_have_the_headers_too(client):
    for response in (client.get("/api/v1/nothing-here"), client.get("/api/v1/auth/me")):
        assert response.status_code in (401, 404)
        assert response.headers["x-content-type-options"] == "nosniff"


def test_swagger_page_is_not_broken_by_the_csp(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert "content-security-policy" not in response.headers
    assert response.headers["x-content-type-options"] == "nosniff"


def test_uploaded_photos_are_served_sandboxed(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, headers, sync_db)
    photo_url = sync_db["complaints"].find_one({"_id": ObjectId(complaint_id)})["photoUrl"]
    response = client.get(photo_url)
    assert response.status_code == 200
    assert "sandbox" in response.headers["content-security-policy"]
    assert response.headers["x-content-type-options"] == "nosniff"


# ---------- CORS ----------

def test_cors_allows_only_the_frontend_origin(client):
    allowed = client.options(HEALTH, headers={"Origin": settings.client_url, "Access-Control-Request-Method": "GET"})
    assert allowed.headers.get("access-control-allow-origin") == settings.client_url
    evil = client.options(HEALTH, headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in evil.headers


# ---------- rate limiting ----------

def test_rate_limiter_unit_behaviour():
    small = SlidingWindowLimiter()
    assert small.check("k", 2, 60, now=0) == (True, 0)
    assert small.check("k", 2, 60, now=1) == (True, 0)
    allowed, retry_after = small.check("k", 2, 60, now=10)
    assert allowed is False and 49 <= retry_after <= 51
    assert small.check("other", 2, 60, now=10) == (True, 0)   # another key is not affected
    assert small.check("k", 2, 60, now=61)[0] is True          # the first attempt has left the window
    small.reset()
    assert small.check("k", 2, 60, now=62) == (True, 0)


def test_login_is_blocked_after_too_many_attempts(client, limits_on):
    for _ in range(settings.rate_limit_login_max):
        assert bad_login(client).status_code == 401
    response = bad_login(client)
    assert response.status_code == 429
    assert int(response.headers["retry-after"]) > 0
    body = response.json()
    assert body["success"] is False and "Too many" in body["message"] and body["errors"] == []
    assert response.headers["x-content-type-options"] == "nosniff"  # even this answer has the headers


def test_a_blocked_client_cannot_log_in_even_with_the_right_password(client, create_user, limits_on):
    create_user(email="citizen@example.com")  # registering counts as 1 register attempt, not login
    for _ in range(settings.rate_limit_login_max):
        bad_login(client, "citizen@example.com")
    right = client.post(LOGIN, json={"email": "citizen@example.com", "password": PASSWORD})
    assert right.status_code == 429


def test_register_has_its_own_limit(client, limits_on):
    for number in range(settings.rate_limit_register_max):
        response = client.post(REGISTER, json={"name": "Person", "email": f"p{number}@example.com", "password": PASSWORD})
        assert response.status_code == 201
    blocked = client.post(REGISTER, json={"name": "Person", "email": "extra@example.com", "password": PASSWORD})
    assert blocked.status_code == 429
    assert bad_login(client).status_code == 401  # login still has its own, separate counter


def test_other_endpoints_are_never_rate_limited(client, create_user, limits_on):
    headers = create_user(email="citizen@example.com")
    for _ in range(30):
        assert client.get(HEALTH).status_code == 200
        assert client.get("/api/v1/auth/me", headers=headers).status_code == 200


def test_forged_forwarded_header_does_not_bypass_the_limit(client, limits_on):
    for number in range(settings.rate_limit_login_max):
        assert bad_login(client, **{"X-Forwarded-For": f"10.0.0.{number}"}).status_code == 401
    assert bad_login(client, **{"X-Forwarded-For": "10.9.9.9"}).status_code == 429  # header ignored by default


def test_forwarded_header_is_used_only_when_trusted(client, limits_on, monkeypatch):
    monkeypatch.setattr(settings, "trust_proxy_headers", True)
    for _ in range(settings.rate_limit_login_max):
        bad_login(client, **{"X-Forwarded-For": "10.1.1.1"})
    assert bad_login(client, **{"X-Forwarded-For": "10.1.1.1"}).status_code == 429
    assert bad_login(client, **{"X-Forwarded-For": "10.2.2.2"}).status_code == 401  # a different visitor


def test_rate_limit_can_be_switched_off(client, limits_on, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    for _ in range(settings.rate_limit_login_max + 5):
        assert bad_login(client).status_code == 401


def test_no_rate_limit_while_testing_by_default(client):
    for _ in range(settings.rate_limit_login_max + 5):
        assert bad_login(client).status_code == 401  # APP_ENV=test


# ---------- request size ----------

def test_oversized_json_body_is_refused_early(client):
    response = client.post(LOGIN, content=b"x" * (settings.max_json_body_kb * 1024 + 1), headers={"content-type": "application/json"})
    assert response.status_code == 413
    assert response.json()["success"] is False


def test_oversized_upload_is_refused(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    big = PNG_BYTES + b"0" * ((settings.max_upload_mb + 2) * 1024 * 1024)
    response = post_complaint(client, headers, complaint_form(sync_db), content=big)
    assert response.status_code == 413
    assert sync_db["complaints"].count_documents({}) == 0


# ---------- injection and validation ----------

@pytest.mark.parametrize("body", [
    {"email": {"$ne": None}, "password": {"$ne": None}},
    {"email": "a@example.com", "password": {"$gt": ""}},
    {"email": ["a@example.com"], "password": PASSWORD},
    {"email": "a@example.com", "password": PASSWORD, "role": "ADMIN"},
])
def test_operators_in_a_login_body_are_rejected(client, create_user, body):
    create_user(email="a@example.com")
    assert client.post(LOGIN, json=body).status_code == 422


def test_mongo_operators_in_query_strings_and_paths_are_never_interpreted(client, create_user, sync_db):
    admin = create_user(email="admin@example.com", role="ADMIN")
    citizen = create_user(email="citizen@example.com")
    make_complaint(client, citizen, sync_db)

    # "status[$ne]" is just an unknown parameter name here. It is ignored, not turned into a MongoDB operator.
    response = client.get("/api/v1/admin/complaints?status[$ne]=SUBMITTED", headers=admin)
    assert response.status_code == 200 and response.json()["data"]["total"] == 1  # a real $ne would give 0
    assert client.get("/api/v1/admin/audit-logs?userId[$ne]=1", headers=admin).status_code == 200

    # A value that is not a plain id or enum is refused
    assert client.get('/api/v1/admin/complaints?categoryId={"$ne":""}', headers=admin).status_code == 400
    assert client.get("/api/v1/admin/complaints?status=%7B%22%24ne%22%3A1%7D", headers=admin).status_code == 422
    assert client.get("/api/v1/admin/complaints/%7B%22%24ne%22%3A1%7D", headers=admin).status_code == 400


def test_register_cannot_choose_role_points_or_badges(client, sync_db):
    response = client.post(REGISTER, json={"name": "Sneaky", "email": "sneaky@example.com", "password": PASSWORD,
                                          "role": "ADMIN", "points": 999, "badges": ["City Champion"], "isActive": True})
    assert response.status_code == 422
    assert sync_db["users"].count_documents({"email": "sneaky@example.com"}) == 0


def test_filename_of_an_upload_is_never_trusted(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    response = post_complaint(client, headers, complaint_form(sync_db), filename="../../../evil<script>.png")
    assert response.status_code == 201
    photo_url = sync_db["complaints"].find_one({})["photoUrl"]
    assert re.fullmatch(r"/uploads/complaints/[0-9a-f]{32}\.(png|jpg|webp)", photo_url)


def test_html_disguised_as_an_image_is_rejected(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    for content, name, kind in ((b"<html><script>alert(1)</script></html>", "page.png", "image/png"),
                                (b"<svg xmlns='http://www.w3.org/2000/svg'><script>1</script></svg>", "x.svg", "image/svg+xml")):
        response = post_complaint(client, headers, complaint_form(sync_db), filename=name, content=content, content_type=kind)
        assert response.status_code in (400, 415, 422)
    assert sync_db["complaints"].count_documents({}) == 0


# ---------- tokens ----------

def make_token(user_id, secret=None, algorithm="HS256", expires_in=3600):
    now = datetime.now(timezone.utc)
    payload = {"sub": user_id, "iat": now, "exp": now + timedelta(seconds=expires_in)}
    return jwt.encode(payload, secret or settings.jwt_secret, algorithm=algorithm)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_bad_tokens_are_all_rejected(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    user_id = str(user_by_email(sync_db, "citizen@example.com")["_id"])
    good = headers["Authorization"].split()[1]
    assert client.get("/api/v1/auth/me", headers=auth(make_token(user_id))).status_code == 200

    tampered = good[:-3] + ("AAA" if not good.endswith("AAA") else "BBB")
    unsigned = jwt.encode({"sub": user_id, "exp": int(time.time()) + 3600}, key="", algorithm="none")
    bad_tokens = {
        "tampered signature": tampered,
        "wrong secret": make_token(user_id, secret="a-completely-different-secret-key-1234567890"),
        "expired": make_token(user_id, expires_in=-10),
        "alg none": unsigned,
        "garbage": "not.a.token",
        "user that does not exist": make_token(str(ObjectId())),
        "id that is not an ObjectId": make_token("123"),
    }
    for name, token in bad_tokens.items():
        response = client.get("/api/v1/auth/me", headers=auth(token))
        assert response.status_code == 401, name
        assert response.json()["success"] is False

    assert client.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": good}).status_code == 401  # no "Bearer"


def test_a_deleted_or_deactivated_user_loses_access_at_once(client, create_user, sync_db):
    headers = create_user(email="citizen@example.com")
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    sync_db["users"].update_one({"email": "citizen@example.com"}, {"$set": {"isActive": False}})
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_weak_jwt_secrets_stop_the_server_from_starting(monkeypatch):
    for secret in ("", "short", "CHANGE_THIS_" + "x" * 40):
        monkeypatch.setattr(settings, "jwt_secret", secret)
        with pytest.raises(RuntimeError):
            validate_settings()


# ---------- what must never leak ----------

def test_passwords_and_hashes_never_appear_in_responses(client, create_user, sync_db):
    register = client.post(REGISTER, json={"name": "Leak Test", "email": "leak@example.com", "password": PASSWORD})
    login = client.post(LOGIN, json={"email": "leak@example.com", "password": PASSWORD})
    token = login.json()["data"]["accessToken"]
    me = client.get("/api/v1/auth/me", headers=auth(token))
    for response in (register, login, me):
        assert "passwordHash" not in response.text and "$2b$" not in response.text and PASSWORD not in response.text
    stored = user_by_email(sync_db, "leak@example.com")["passwordHash"]
    assert stored.startswith("$2") and stored != PASSWORD


def test_login_does_not_reveal_whether_an_email_exists(client, create_user):
    create_user(email="real@example.com")
    unknown = bad_login(client, "ghost@example.com")
    wrong_password = bad_login(client, "real@example.com")
    assert unknown.status_code == wrong_password.status_code == 401
    assert unknown.json() == wrong_password.json()


def test_unexpected_errors_show_a_safe_message(client, create_user, monkeypatch):
    from app.services import department_service

    async def explode():
        raise RuntimeError("SECRET: mongodb://user:hunter2@cluster/db")

    monkeypatch.setattr(department_service, "list_active_departments", explode)
    # Reuse the session client: the async MongoDB driver is tied to the event loop it was created on,
    # so a second TestClient (which starts its own loop per request) breaks against a real database.
    # We only switch off its "re-raise server errors" behaviour for this one test.
    monkeypatch.setattr(client._transport, "raise_server_exceptions", False)
    quiet = client
    token = quiet.post(REGISTER, json={"name": "Someone", "email": "someone@example.com", "password": PASSWORD})
    login = quiet.post(LOGIN, json={"email": "someone@example.com", "password": PASSWORD}).json()["data"]["accessToken"]
    response = quiet.get("/api/v1/departments", headers=auth(login))
    assert response.status_code == 500
    assert response.json() == {"success": False, "message": "Internal server error", "errors": []}
    assert "hunter2" not in response.text and "Traceback" not in response.text
