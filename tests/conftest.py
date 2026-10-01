import os

# These MUST be set before the app is imported
os.environ["APP_ENV"] = "test"
os.environ["MONGO_DB_NAME"] = "civic_issue_test_db"
os.environ["JWT_SECRET"] = "test-only-secret-key-for-automated-tests-1234567890"

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import settings
from app.main import app

TEST_PASSWORD = "Passw0rd123"


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


@pytest.fixture(autouse=True)
def clean_users(sync_db):
    """Every test starts with an empty users collection."""
    sync_db["users"].delete_many({})
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