import asyncio
import re
from pathlib import Path

import pytest
from civic_test_helpers import (
    COMPLAINTS_URL,
    PNG_BYTES,
    complaint_form,
    post_complaint,
)
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.models.counter import next_sequence


@pytest.fixture(autouse=True)
def seeded(clean_collections, seed_catalog_only):
    seed_catalog_only()


def test_citizen_creates_complaint(client, create_user, sync_db):
    headers = create_user()

    response = post_complaint(client, headers, complaint_form(sync_db))
    data = response.json()["data"]

    assert response.status_code == 201
    assert re.fullmatch(r"CIV-\d{4}-\d{6}", data["complaintNumber"])
    assert data["status"] == "SUBMITTED"
    assert data["department"]["code"] == "ROAD"
    assert data["photoUrl"].startswith("/uploads/complaints/")
    assert data["isAnonymous"] is False


@pytest.mark.parametrize(
    "category_code, department_code",
    [
        ("POTHOLE", "ROAD"),
        ("GARBAGE", "SANITATION"),
        ("ILLEGAL_PARKING", "TRAFFIC"),
        ("NOISE_COMPLAINT", "ENVIRONMENT"),
    ],
)
def test_department_is_assigned_from_category(
    client, create_user, sync_db, category_code, department_code
):
    headers = create_user()

    response = post_complaint(client, headers, complaint_form(sync_db, category_code))

    assert response.status_code == 201
    assert response.json()["data"]["department"]["code"] == department_code


def test_changing_category_mapping_changes_department(client, create_user, sync_db):
    headers = create_user()
    traffic = sync_db["departments"].find_one({"code": "TRAFFIC"})
    sync_db["categories"].update_one({"code": "POTHOLE"}, {"$set": {"departmentId": traffic["_id"]}})

    response = post_complaint(client, headers, complaint_form(sync_db))

    assert response.json()["data"]["department"]["code"] == "TRAFFIC"


def test_bad_category_is_rejected(client, create_user, sync_db):
    headers = create_user()

    malformed = post_complaint(client, headers, complaint_form(sync_db, categoryId="not-an-id"))
    unknown = post_complaint(client, headers, complaint_form(sync_db, categoryId="64b7f0000000000000000000"))
    form_for_inactive = complaint_form(sync_db, "GARBAGE")
    sync_db["categories"].update_one({"code": "GARBAGE"}, {"$set": {"isActive": False}})
    inactive = post_complaint(client, headers, form_for_inactive)

    assert malformed.status_code == 400
    assert unknown.status_code == 404
    assert inactive.status_code == 404


def test_invalid_coordinates_are_rejected(client, create_user, sync_db):
    headers = create_user()

    assert post_complaint(client, headers, complaint_form(sync_db, latitude="120")).status_code == 422
    assert post_complaint(client, headers, complaint_form(sync_db, longitude="-200")).status_code == 422
    assert post_complaint(client, headers, complaint_form(sync_db, latitude="abc")).status_code == 422


def test_missing_photo_is_rejected(client, create_user, sync_db):
    headers = create_user()

    response = client.post(COMPLAINTS_URL, data=complaint_form(sync_db), headers=headers)

    assert response.status_code == 422


def test_fake_image_is_rejected(client, create_user, sync_db):
    headers = create_user()

    response = post_complaint(
        client, headers, complaint_form(sync_db),
        filename="photo.png", content=b"this is not an image", content_type="image/png",
    )

    assert response.status_code == 400


def test_oversized_photo_is_rejected(client, create_user, sync_db, monkeypatch):
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    headers = create_user()
    big_png = b"\x89PNG\r\n\x1a\n" + b"0" * (2 * 1024 * 1024)

    response = post_complaint(client, headers, complaint_form(sync_db), content=big_png)

    assert response.status_code == 413


def test_unauthenticated_user_cannot_create(client, sync_db):
    response = post_complaint(client, {}, complaint_form(sync_db))

    assert response.status_code == 401


def test_worker_cannot_create(client, create_user, sync_db):
    headers = create_user(email="worker@example.com", role="WORKER")

    response = post_complaint(client, headers, complaint_form(sync_db))

    assert response.status_code == 403


def test_client_cannot_choose_department_or_reporter(client, create_user, sync_db):
    headers = create_user()
    my_id = client.get("/api/v1/auth/me", headers=headers).json()["data"]["id"]
    traffic = sync_db["departments"].find_one({"code": "TRAFFIC"})
    form = complaint_form(
        sync_db,
        departmentId=str(traffic["_id"]),
        reportedBy="000000000000000000000000",
        status="RESOLVED",
    )

    data = post_complaint(client, headers, form).json()["data"]

    assert data["department"]["code"] == "ROAD"
    assert data["reportedBy"] == my_id
    assert data["status"] == "SUBMITTED"


def test_unsafe_filename_is_replaced_and_photo_is_served(client, create_user, sync_db):
    headers = create_user()

    response = post_complaint(
        client, headers, complaint_form(sync_db), filename="../../evil.php.png"
    )
    photo_url = response.json()["data"]["photoUrl"]

    assert "evil" not in photo_url and ".." not in photo_url
    assert photo_url.endswith(".png")
    assert (Path(settings.upload_dir) / photo_url.removeprefix("/uploads/")).exists()
    served = client.get(photo_url)
    assert served.status_code == 200
    assert served.content == PNG_BYTES


def test_complaint_numbers_increase(client, create_user, sync_db):
    headers = create_user()

    # spot=0,1,2 are far apart, so none of them is treated as a duplicate
    numbers = [
        post_complaint(client, headers, complaint_form(sync_db, spot=spot)).json()["data"]["complaintNumber"]
        for spot in range(3)
    ]

    assert [int(number.split("-")[2]) for number in numbers] == [1, 2, 3]


def test_complaint_numbers_are_unique_under_concurrency():
    async def run():
        mongo = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
        try:
            db = mongo[settings.mongo_db_name]
            return await asyncio.gather(*(next_sequence(db, "complaint-test") for _ in range(25)))
        finally:
            await mongo.close()

    numbers = asyncio.run(run())

    assert sorted(numbers) == list(range(1, 26))


def test_location_is_geojson_and_indexed(client, create_user, sync_db):
    headers = create_user()
    post_complaint(client, headers, complaint_form(sync_db, latitude="19.1867", longitude="73.1920"))

    stored = sync_db["complaints"].find_one()
    indexes = sync_db["complaints"].index_information()

    assert stored["location"] == {"type": "Point", "coordinates": [73.192, 19.1867]}
    assert any(index["key"] == [("location", "2dsphere")] for index in indexes.values())


def test_citizen_sees_only_own_complaints(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    for spot in (0, 1):
        post_complaint(client, headers_a, complaint_form(sync_db, spot=spot))
    post_complaint(client, headers_b, complaint_form(sync_db, spot=2))

    list_a = client.get(COMPLAINTS_URL, headers=headers_a).json()["data"]
    list_b = client.get(COMPLAINTS_URL, headers=headers_b).json()["data"]

    assert list_a["total"] == 2
    assert list_b["total"] == 1


def test_other_citizen_cannot_open_complaint_but_admin_can(client, create_user, sync_db):
    headers_a = create_user(email="a@example.com")
    headers_b = create_user(email="b@example.com")
    admin_headers = create_user(email="admin@example.com", role="ADMIN")
    complaint_id = post_complaint(client, headers_a, complaint_form(sync_db)).json()["data"]["id"]
    url = f"{COMPLAINTS_URL}/{complaint_id}"

    assert client.get(url, headers=headers_a).status_code == 200
    assert client.get(url, headers=headers_b).status_code == 404
    assert client.get(url, headers=admin_headers).status_code == 200


def test_worker_cannot_list_complaints(client, create_user):
    headers = create_user(email="worker@example.com", role="WORKER")

    assert client.get(COMPLAINTS_URL, headers=headers).status_code == 403


def test_status_filter_and_pagination(client, create_user, sync_db):
    headers = create_user()
    for spot in (0, 1):
        post_complaint(client, headers, complaint_form(sync_db, spot=spot))

    submitted = client.get(f"{COMPLAINTS_URL}?status=SUBMITTED", headers=headers).json()["data"]
    resolved = client.get(f"{COMPLAINTS_URL}?status=RESOLVED", headers=headers).json()["data"]
    first_page = client.get(f"{COMPLAINTS_URL}?limit=1&page=1", headers=headers).json()["data"]
    invalid = client.get(f"{COMPLAINTS_URL}?status=NOPE", headers=headers)

    assert submitted["total"] == 2
    assert resolved["total"] == 0
    assert len(first_page["items"]) == 1 and first_page["total"] == 2
    assert invalid.status_code == 422
