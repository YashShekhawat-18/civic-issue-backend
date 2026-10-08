from pathlib import Path

import pytest
from civic_test_helpers import (
    BASE_LONGITUDE,
    COMPLAINTS_URL,
    category_id,
    complaint_form,
    latitude_for,
    post_complaint,
    user_id,
)

from app.core.config import settings

NEARBY_URL = f"{COMPLAINTS_URL}/nearby"


@pytest.fixture(autouse=True)
def seeded(clean_collections, seed_catalog_only):
    seed_catalog_only()


def nearby_params(meters_north=0, spot=0, **changes):
    params = {"latitude": latitude_for(spot, meters_north), "longitude": BASE_LONGITUDE}
    params.update(changes)
    return params


def test_nearby_same_category_is_reported_as_duplicate(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    first = post_complaint(client, headers_a, complaint_form(sync_db)).json()["data"]

    response = post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))
    data = response.json()["data"]

    assert response.status_code == 200  # nothing was created, so not 201
    assert data["duplicate"] is True
    assert data["existingComplaint"]["id"] == first["id"]
    assert 40 <= data["existingComplaint"]["distanceMeters"] <= 60
    assert data["canUpvote"] is True
    assert data["upvoteUrl"].endswith(f"/{first['id']}/upvote")
    assert sync_db["complaints"].count_documents({}) == 1


def test_duplicate_response_hides_anonymous_reporter(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    a_id = user_id(client, headers_a)
    post_complaint(client, headers_a, complaint_form(sync_db, isAnonymous="true"))

    response = post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))
    existing = response.json()["data"]["existingComplaint"]

    assert response.status_code == 200
    assert existing["isAnonymous"] is True
    assert existing["reporter"] is None
    assert "reportedBy" not in existing
    assert a_id not in response.text
    assert "a@example.com" not in response.text


def test_duplicate_response_shows_only_the_name_of_an_open_reporter(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    a_id = user_id(client, headers_a)
    post_complaint(client, headers_a, complaint_form(sync_db))

    response = post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))
    existing = response.json()["data"]["existingComplaint"]

    assert existing["reporter"] == {"name": "Test User"}
    assert "reportedBy" not in existing
    assert a_id not in response.text
    assert "a@example.com" not in response.text


def test_far_away_complaint_is_not_a_duplicate(client, create_user, sync_db):
    headers = create_user()
    post_complaint(client, headers, complaint_form(sync_db))

    response = post_complaint(client, headers, complaint_form(sync_db, meters_north=300))

    assert response.status_code == 201
    assert sync_db["complaints"].count_documents({}) == 2


def test_different_category_is_not_a_duplicate(client, create_user, sync_db):
    headers = create_user()
    post_complaint(client, headers, complaint_form(sync_db, "POTHOLE"))

    response = post_complaint(client, headers, complaint_form(sync_db, "GARBAGE"))

    assert response.status_code == 201
    assert response.json()["data"]["department"]["code"] == "SANITATION"


def test_resolved_complaint_is_not_a_duplicate(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db))
    sync_db["complaints"].update_one({}, {"$set": {"status": "RESOLVED"}})

    response = post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))

    assert response.status_code == 201


def test_in_progress_complaint_is_still_a_duplicate(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db))
    sync_db["complaints"].update_one({}, {"$set": {"status": "IN_PROGRESS"}})

    response = post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))

    assert response.status_code == 200
    assert response.json()["data"]["duplicate"] is True


def test_duplicate_radius_is_configurable(client, create_user, sync_db, monkeypatch):
    monkeypatch.setattr(settings, "duplicate_radius_meters", 20)
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db))

    response = post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))

    assert response.status_code == 201  # 50 m is outside a 20 m radius
    assert sync_db["complaints"].count_documents({}) == 2


def test_reporting_your_own_issue_again_says_so(client, create_user, sync_db):
    headers = create_user()
    post_complaint(client, headers, complaint_form(sync_db))

    response = post_complaint(client, headers, complaint_form(sync_db, meters_north=30))
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["existingComplaint"]["isOwnComplaint"] is True
    assert data["canUpvote"] is False
    assert "already reported" in data["message"]


def test_duplicate_does_not_save_a_photo(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db))
    photo_folder = Path(settings.upload_dir) / "complaints"
    files_before = sorted(path.name for path in photo_folder.iterdir())

    post_complaint(client, headers_b, complaint_form(sync_db, meters_north=50))

    assert sorted(path.name for path in photo_folder.iterdir()) == files_before


def test_nearby_lists_open_complaints_with_distance(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db))

    response = client.get(NEARBY_URL, params=nearby_params(meters_north=50), headers=headers_b)
    data = response.json()["data"]

    assert response.status_code == 200
    assert data["count"] == 1
    item = data["items"][0]
    assert 40 <= item["distanceMeters"] <= 60
    assert "reportedBy" not in item
    assert item["hasUpvoted"] is False
    assert item["isOwnComplaint"] is False


def test_nearby_ignores_far_and_resolved_complaints(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db))

    far = client.get(NEARBY_URL, params=nearby_params(spot=1), headers=headers_b)  # about 1.1 km away
    sync_db["complaints"].update_one({}, {"$set": {"status": "RESOLVED"}})
    resolved = client.get(NEARBY_URL, params=nearby_params(), headers=headers_b)

    assert far.json()["data"]["count"] == 0
    assert resolved.json()["data"]["count"] == 0


def test_nearby_can_filter_by_category(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    post_complaint(client, headers_a, complaint_form(sync_db, "POTHOLE"))

    garbage = client.get(
        NEARBY_URL, params=nearby_params(categoryId=category_id(sync_db, "GARBAGE")), headers=headers_b
    )
    pothole = client.get(
        NEARBY_URL, params=nearby_params(categoryId=category_id(sync_db, "POTHOLE")), headers=headers_b
    )
    malformed = client.get(NEARBY_URL, params=nearby_params(categoryId="not-an-id"), headers=headers_b)

    assert garbage.json()["data"]["count"] == 0
    assert pothole.json()["data"]["count"] == 1
    assert malformed.status_code == 400


def test_nearby_validates_input_and_roles(client, create_user):
    citizen = create_user(email="a@example.com")
    worker = create_user(email="worker@example.com", role="WORKER")

    assert client.get(NEARBY_URL, params=nearby_params()).status_code == 401
    assert client.get(NEARBY_URL, params=nearby_params(), headers=worker).status_code == 403
    assert client.get(NEARBY_URL, params=nearby_params(latitude=120), headers=citizen).status_code == 422
    assert client.get(NEARBY_URL, params=nearby_params(radius=5001), headers=citizen).status_code == 422
    assert client.get(NEARBY_URL, params=nearby_params(radius=5), headers=citizen).status_code == 422
    assert client.get(NEARBY_URL, headers=citizen).status_code == 422
