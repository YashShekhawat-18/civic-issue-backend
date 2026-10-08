import asyncio

import pytest
from bson import ObjectId
from civic_test_helpers import (
    BASE_LONGITUDE,
    COMPLAINTS_URL,
    complaint_form,
    latitude_for,
    post_complaint,
)
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.core.errors import ApiError
from app.services import upvote_service


@pytest.fixture(autouse=True)
def seeded(clean_collections, seed_catalog_only):
    seed_catalog_only()


def make_complaint(client, headers, sync_db, **changes):
    return post_complaint(client, headers, complaint_form(sync_db, **changes)).json()["data"]["id"]


def upvote_url(complaint_id):
    return f"{COMPLAINTS_URL}/{complaint_id}/upvote"


def stored_count(sync_db, complaint_id):
    return sync_db["complaints"].find_one({"_id": ObjectId(complaint_id)})["upvoteCount"]


def test_citizen_can_upvote_another_citizens_complaint(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)

    response = client.post(upvote_url(complaint_id), headers=headers_b)
    data = response.json()["data"]

    assert response.status_code == 201
    assert data["upvoteCount"] == 1
    assert data["hasUpvoted"] is True
    assert stored_count(sync_db, complaint_id) == 1
    assert sync_db["upvotes"].count_documents({}) == 1


def test_second_upvote_by_the_same_citizen_is_rejected(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)
    client.post(upvote_url(complaint_id), headers=headers_b)

    response = client.post(upvote_url(complaint_id), headers=headers_b)

    assert response.status_code == 409
    assert stored_count(sync_db, complaint_id) == 1
    assert sync_db["upvotes"].count_documents({}) == 1


def test_citizen_cannot_upvote_own_complaint(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)

    response = client.post(upvote_url(complaint_id), headers=headers_a)

    assert response.status_code == 403
    assert stored_count(sync_db, complaint_id) == 0


def test_cannot_upvote_a_resolved_complaint(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)
    sync_db["complaints"].update_one({}, {"$set": {"status": "RESOLVED"}})

    response = client.post(upvote_url(complaint_id), headers=headers_b)

    assert response.status_code == 409


def test_bad_complaint_ids_are_rejected(client, create_user):
    headers = create_user()

    assert client.post(upvote_url("not-an-id"), headers=headers).status_code == 400
    assert client.post(upvote_url("64b7f0000000000000000000"), headers=headers).status_code == 404


def test_removing_an_upvote_and_the_counter_never_goes_below_zero(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)
    client.post(upvote_url(complaint_id), headers=headers_b)

    removed = client.delete(upvote_url(complaint_id), headers=headers_b)
    removed_again = client.delete(upvote_url(complaint_id), headers=headers_b)

    assert removed.status_code == 200
    assert removed.json()["data"] == {
        "complaintId": complaint_id, "upvoteCount": 0, "hasUpvoted": False,
    }
    assert removed_again.status_code == 404
    assert stored_count(sync_db, complaint_id) == 0

    # Even if the counter is wrong (0) while an upvote exists, removing it must not give -1
    client.post(upvote_url(complaint_id), headers=headers_b)
    sync_db["complaints"].update_one({"_id": ObjectId(complaint_id)}, {"$set": {"upvoteCount": 0}})
    response = client.delete(upvote_url(complaint_id), headers=headers_b)

    assert response.status_code == 200
    assert stored_count(sync_db, complaint_id) == 0


def test_only_citizens_can_upvote(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    worker = create_user(email="worker@example.com", role="WORKER")
    admin = create_user(email="admin@example.com", role="ADMIN")
    complaint_id = make_complaint(client, headers_a, sync_db)

    assert client.post(upvote_url(complaint_id)).status_code == 401
    assert client.post(upvote_url(complaint_id), headers=worker).status_code == 403
    assert client.post(upvote_url(complaint_id), headers=admin).status_code == 403
    assert client.delete(upvote_url(complaint_id), headers=worker).status_code == 403


def test_unique_index_on_user_and_complaint_exists(client, sync_db):
    indexes = sync_db["upvotes"].index_information()

    assert any(
        index["key"] == [("userId", 1), ("complaintId", 1)] and index.get("unique") is True
        for index in indexes.values()
    )


def test_concurrent_upvotes_are_counted_correctly(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)

    async def run():
        mongo = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
        try:
            db = mongo[settings.mongo_db_name]
            same_user = ObjectId()
            same_user_results = await asyncio.gather(
                *(upvote_service.add_upvote(complaint_id, same_user, db=db) for _ in range(5)),
                return_exceptions=True,
            )
            many_users = await asyncio.gather(
                *(upvote_service.add_upvote(complaint_id, ObjectId(), db=db) for _ in range(10))
            )
            return same_user_results, many_users
        finally:
            await mongo.close()

    same_user_results, many_users = asyncio.run(run())

    successes = [result for result in same_user_results if isinstance(result, dict)]
    failures = [result for result in same_user_results if isinstance(result, ApiError)]
    assert len(successes) == 1 and len(failures) == 4  # five clicks at once, one upvote
    assert all(failure.status_code == 409 for failure in failures)
    assert len(many_users) == 10
    assert stored_count(sync_db, complaint_id) == 11
    assert sync_db["upvotes"].count_documents({}) == 11


def test_upvoted_state_is_visible_to_the_voter(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    complaint_id = make_complaint(client, headers_a, sync_db)
    client.post(upvote_url(complaint_id), headers=headers_b)

    nearby = client.get(
        f"{COMPLAINTS_URL}/nearby",
        params={"latitude": latitude_for(meters_north=50), "longitude": BASE_LONGITUDE},
        headers=headers_b,
    ).json()["data"]["items"][0]
    duplicate = post_complaint(
        client, headers_b, complaint_form(sync_db, meters_north=30)
    ).json()["data"]

    assert nearby["hasUpvoted"] is True
    assert nearby["upvoteCount"] == 1
    assert duplicate["canUpvote"] is False
    assert "already upvoted" in duplicate["message"]
