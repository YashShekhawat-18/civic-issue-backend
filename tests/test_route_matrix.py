"""Calls EVERY endpoint as every kind of visitor and checks who is let in.

The list of endpoints and the allowed roles come from scripts/generate_api_docs.py, which also
writes the documentation. So this test proves the documentation tells the truth.
"""
import importlib.util
import re
from pathlib import Path

import pytest
from bson import ObjectId
from phase1011_support import clean_phase1011, department_id, user_by_email  # noqa: F401
from phase67_support import clean_notifications, make_worker, seeded  # noqa: F401
from phase89_support import clean_ledger  # noqa: F401

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "generate_api_docs.py"
spec = importlib.util.spec_from_file_location("generate_api_docs", SCRIPT)
docs_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(docs_script)

ENDPOINTS = docs_script.collect_endpoints()
ROLES = ("CITIZEN", "WORKER", "ADMIN")
# Existing routes from earlier phases whose "who can call" is covered by their own tests.
SKIP = {("GET", "/api/v1/departments"), ("GET", "/api/v1/categories")}


def fill(path):
    """Replaces {complaint_id} and friends with an id that does not exist."""
    return re.sub(r"\{[^}]+\}", str(ObjectId()), path)


def call(client, method, path, headers=None):
    # "{}" is valid JSON but invalid for every body, so allowed callers get 422/404/400, never 401/403
    kwargs = {"headers": headers or {}}
    if method in ("POST", "PATCH", "PUT"):
        kwargs["json"] = {}
    return client.request(method, fill(path), **kwargs)


@pytest.fixture
def visitors(client, create_user, sync_db):
    return {
        "CITIZEN": create_user(email="citizen@example.com"),
        "WORKER": make_worker(create_user, sync_db, "worker@example.com"),
        "ADMIN": create_user(email="admin@example.com", role="ADMIN"),
    }


def test_the_endpoint_list_is_complete_and_uses_every_kind_of_rule():
    assert len(ENDPOINTS) >= 45
    kinds = {e["who"] for e in ENDPOINTS}
    assert {"Public", "Any logged-in user", "ADMIN", "WORKER", "CITIZEN"} <= kinds


@pytest.mark.parametrize("endpoint", ENDPOINTS, ids=lambda e: f"{e['method']} {e['path']}")
def test_every_endpoint_lets_in_exactly_the_documented_visitors(client, visitors, endpoint):
    method, path, who = endpoint["method"], endpoint["path"], endpoint["who"]
    if (method, path) in SKIP:
        pytest.skip("covered by the Phase 3 tests")

    anonymous = call(client, method, path)
    if who == "Public":
        assert anonymous.status_code not in (401, 403)
        return
    assert anonymous.status_code == 401, "an endpoint that needs a login answered without one"

    allowed = set(ROLES) if who == "Any logged-in user" else {r.strip() for r in who.split(",")}
    for role in ROLES:
        status = call(client, method, path, visitors[role]).status_code
        if role in allowed:
            assert status not in (401, 403), f"{role} should be allowed but got {status}"
        else:
            assert status == 403, f"{role} should be refused but got {status}"


def test_every_admin_or_worker_endpoint_is_documented_as_restricted():
    for e in ENDPOINTS:
        if "/admin" in e["path"]:
            assert e["who"] == "ADMIN"
        if "/worker/" in e["path"]:
            assert e["who"] == "WORKER"


def test_no_two_routes_share_the_same_method_and_url():
    """FastAPI warns "Duplicate Operation ID" when two routes have the same method + URL.

    Which of the two would answer depends on registration order (and on the FastAPI version), so
    a duplicate is a bug waiting to happen. We turn that warning into a test failure.
    """
    import warnings

    from app.main import app

    saved = app.openapi_schema
    app.openapi_schema = None  # force a fresh build, otherwise the cached schema hides the warning
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("error", message="Duplicate Operation ID")
            app.openapi()
    finally:
        app.openapi_schema = saved
