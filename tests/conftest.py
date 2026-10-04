import asyncio
import os
import shutil
import tempfile

# These MUST be set before the app is imported
TEST_UPLOAD_DIR = tempfile.mkdtemp(prefix="civic_test_uploads_")
os.environ["APP_ENV"] = "test"
os.environ["MONGO_DB_NAME"] = "civic_issue_test_db"
os.environ["JWT_SECRET"] = "test-only-secret-key-for-automated-tests-1234567890"
os.environ["UPLOAD_DIR"] = TEST_UPLOAD_DIR
os.environ["SEED_ADMIN_EMAIL"] = "seed-admin@example.com"
os.environ["SEED_ADMIN_PASSWORD"] = "SeedAdminPass123"
os.environ["SEED_WORKER_PASSWORD"] = "SeedWorkerPass123"

import pytest
from fastapi.testclient import TestClient
from pymongo import AsyncMongoClient, MongoClient

from app.core.config import settings
from app.main import app

TEST_PASSWORD = "Passw0rd123"
COLLECTIONS_TO_CLEAN = ("users", "departments", "categories", "badges", "complaints", "counters")


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def sync_db():
    """Plain synchronous connection, used only for test set-up and clean-up."""
    assert settings.mongo_db_name.endswith("_test_db"), "Refusing to touch a non-test database"
    mongo = MongoClient(settings.mongo_uri, serverSelectionTimeoutMS=5000)
    yield mongo[settings.mongo_db_name]
    mongo.drop_database(settings.mongo_db_name)
    mongo.close()


@pytest.fixture(scope="session", autouse=True)
def remove_test_uploads():
    yield
    shutil.rmtree(TEST_UPLOAD_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_collections(sync_db):
    """Every test starts with empty collections."""
    for name in COLLECTIONS_TO_CLEAN:
        sync_db[name].delete_many({})
    yield


@pytest.fixture
def create_user(client, sync_db):
    """Registers a user, optionally gives them a role, logs in, returns auth headers."""

    def _create(email="user@example.com", role="CITIZEN"):
        client.post(
            "/api/v1/auth/register",
            json={"name": "Test User", "email": email, "password": TEST_PASSWORD},
        )
        if role != "CITIZEN":
            sync_db["users"].update_one({"email": email}, {"$set": {"role": role}})
        response = client.post(
            "/api/v1/auth/login", json={"email": email, "password": TEST_PASSWORD}
        )
        token = response.json()["data"]["accessToken"]
        return {"Authorization": f"Bearer {token}"}

    return _create


def _run_seed_function(seed_function):
    async def _run():
        mongo = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
        try:
            await seed_function(mongo[settings.mongo_db_name])
        finally:
            await mongo.close()

    asyncio.run(_run())


@pytest.fixture
def seed_database(sync_db):
    """Returns a function that runs the full seed (departments, categories, users, badges)."""
    from app import seed

    return lambda: _run_seed_function(seed.run_seed)


@pytest.fixture
def seed_catalog_only(sync_db):
    """Faster: only departments and categories."""
    from app import seed

    return lambda: _run_seed_function(seed.seed_catalog)