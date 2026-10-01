from fastapi import APIRouter, Depends

from app.core.dependencies import require_roles
from app.main import app
from app.models.user import Role

# Temporary routes that exist only while tests run.
# They prove that require_roles() works before we use it on real routes.
temp_router = APIRouter(prefix="/__test__")


@temp_router.get("/admin-only")
async def admin_only(user: dict = Depends(require_roles(Role.ADMIN))):
    return {"ok": True}


@temp_router.get("/worker-or-admin")
async def worker_or_admin(user: dict = Depends(require_roles(Role.WORKER, Role.ADMIN))):
    return {"ok": True}


app.include_router(temp_router)


def test_no_token_gets_401(client):
    assert client.get("/__test__/admin-only").status_code == 401


def test_citizen_cannot_access_admin_route(client, create_user):
    headers = create_user(email="citizen@example.com", role="CITIZEN")

    assert client.get("/__test__/admin-only", headers=headers).status_code == 403


def test_worker_cannot_access_admin_route(client, create_user):
    headers = create_user(email="worker@example.com", role="WORKER")

    assert client.get("/__test__/admin-only", headers=headers).status_code == 403


def test_admin_can_access_admin_route(client, create_user):
    headers = create_user(email="admin@example.com", role="ADMIN")

    assert client.get("/__test__/admin-only", headers=headers).status_code == 200


def test_worker_can_access_worker_route(client, create_user):
    headers = create_user(email="worker2@example.com", role="WORKER")

    assert client.get("/__test__/worker-or-admin", headers=headers).status_code == 200