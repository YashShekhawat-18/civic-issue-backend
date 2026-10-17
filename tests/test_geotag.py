"""Geotagged photos: citizens' report photos and workers' after-fix photos."""
import io

import pytest
from civic_test_helpers import BASE_LONGITUDE, COMPLAINTS_URL, complaint_form, latitude_for, post_complaint
from geotag_support import BASE_JPEG, geotagged_jpeg, untagged_jpeg
from phase67_support import (  # noqa: F401  (the fixtures must be imported to be active)
    WORKER_URL,
    clean_notifications,
    make_complaint,
    make_worker,
    resolve_with_photo,
    seeded,
    set_status,
    stored_complaint,
)

from app.core.config import settings
from app.services.geotag_service import distance_meters, read_gps, write_gps


# ---------- reading and writing the GPS position ----------

@pytest.mark.parametrize("lat, lng", [(19.1867, 73.1920), (-33.8688, 151.2093), (40.7128, -74.006), (0.5, -0.25)])
def test_gps_round_trip_in_all_four_hemispheres(lat, lng):
    latitude, longitude = read_gps(write_gps(BASE_JPEG, lat, lng))
    assert latitude == pytest.approx(lat, abs=1e-5)
    assert longitude == pytest.approx(lng, abs=1e-5)


def test_the_photo_still_opens_after_geotagging():
    from PIL import Image  # only the test needs Pillow, as an independent check

    image = Image.open(io.BytesIO(write_gps(BASE_JPEG, 19.1, 73.1)))
    assert image.size == (48, 32)
    gps = image.getexif().get_ifd(0x8825)
    assert gps[1] == "N" and gps[3] == "E"


def test_writing_twice_keeps_one_position():
    twice = write_gps(write_gps(BASE_JPEG, 10.0, 20.0), 19.5, 73.5)
    assert read_gps(twice) == pytest.approx((19.5, 73.5), abs=1e-5)
    assert twice.count(b"Exif\x00\x00") == 1


def test_no_gps_cases_return_none_and_never_raise():
    assert read_gps(untagged_jpeg()) is None
    assert read_gps(b"") is None
    assert read_gps(b"not an image") is None
    assert read_gps(b"\x89PNG\r\n\x1a\n" + b"data") is None
    assert read_gps(b"\xff\xd8\xff\xe1\x00\x08Exif\x00\x00") is None            # empty Exif block
    assert read_gps(write_gps(BASE_JPEG, 0.0, 0.0)) is None                       # 0,0 means "no fix"
    broken = write_gps(BASE_JPEG, 19.1, 73.1)
    assert read_gps(broken[:40]) is None                                          # cut off in the middle


def test_distance_formula():
    assert distance_meters(19.0, 73.0, 19.0, 73.0) == 0
    assert distance_meters(19.0, 73.0, 19.001, 73.0) == pytest.approx(111.2, abs=1)
    assert distance_meters(19.0, 73.0, 19.0, 73.001) == pytest.approx(105.1, abs=1)  # a degree of longitude is shorter here


# ---------- citizen report photo ----------

def test_geotagged_report_is_accepted_and_the_photo_position_is_stored(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    form = complaint_form(sync_db)
    response = post_complaint(client, citizen, form)
    assert response.status_code == 201
    assert response.json()["data"]["photoGeotagged"] is True
    stored = sync_db["complaints"].find_one({})
    assert stored["photoLocation"]["coordinates"] == pytest.approx([float(form["longitude"]), float(form["latitude"])], abs=1e-5)


def test_report_photo_without_gps_is_rejected(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    response = post_complaint(client, citizen, complaint_form(sync_db), content=untagged_jpeg())
    assert response.status_code == 422
    assert "no GPS location" in response.json()["errors"][0]["message"]
    assert response.json()["errors"][0]["field"] == "photo"
    assert sync_db["complaints"].count_documents({}) == 0


def test_report_png_photo_is_rejected_because_it_has_no_gps(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    png = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"
    response = post_complaint(client, citizen, complaint_form(sync_db), content=png, filename="a.png", content_type="image/png")
    assert response.status_code == 422


def test_report_photo_taken_far_from_the_pin_is_rejected(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    form = complaint_form(sync_db)
    far = geotagged_jpeg(float(form["latitude"]) + 0.01, float(form["longitude"]))  # about 1.1 km away
    response = post_complaint(client, citizen, form, content=far)
    assert response.status_code == 422
    message = response.json()["errors"][0]["message"]
    assert "from the pinned location" in message and "300 m" in message
    assert sync_db["complaints"].count_documents({}) == 0


def test_report_photo_a_little_off_the_pin_is_accepted(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    form = complaint_form(sync_db)
    near = geotagged_jpeg(float(form["latitude"]) + 0.002, float(form["longitude"]))  # about 220 m
    assert post_complaint(client, citizen, form, content=near).status_code == 201


def test_the_rule_can_be_switched_off(client, create_user, sync_db, monkeypatch):
    monkeypatch.setattr(settings, "require_photo_gps", False)
    citizen = create_user(email="citizen@example.com")
    response = post_complaint(client, citizen, complaint_form(sync_db), content=untagged_jpeg())
    assert response.status_code == 201
    assert response.json()["data"]["photoGeotagged"] is False


# ---------- worker after-fix photo ----------

def started_complaint(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    assert set_status(client, worker, complaint_id, "IN_PROGRESS").status_code == 200
    return citizen, worker, complaint_id


def test_worker_resolves_with_a_geotagged_photo(client, create_user, sync_db):
    citizen, worker, complaint_id = started_complaint(client, create_user, sync_db)
    response = resolve_with_photo(client, worker, complaint_id, note="Filled with asphalt")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["status"] == "RESOLVED"
    assert data["resolutionPhotoUrl"].startswith("/uploads/resolutions/")
    stored = stored_complaint(sync_db, complaint_id)
    assert stored["resolutionPhotoLocation"]["coordinates"] == pytest.approx(
        stored["location"]["coordinates"], abs=1e-5
    )
    # the citizen sees the proof photo too
    mine = client.get(f"{COMPLAINTS_URL}/{complaint_id}", headers=citizen).json()["data"]
    assert mine["resolutionPhotoUrl"] == data["resolutionPhotoUrl"]
    assert mine["status"] == "RESOLVED"


def test_worker_photo_without_gps_is_rejected_and_nothing_changes(client, create_user, sync_db):
    _, worker, complaint_id = started_complaint(client, create_user, sync_db)
    response = resolve_with_photo(client, worker, complaint_id, content=untagged_jpeg())
    assert response.status_code == 422
    assert "no GPS location" in response.json()["errors"][0]["message"]
    stored = stored_complaint(sync_db, complaint_id)
    assert stored["status"] == "IN_PROGRESS"
    assert stored["resolutionPhotoUrl"] is None


def test_worker_photo_taken_far_away_is_rejected(client, create_user, sync_db):
    _, worker, complaint_id = started_complaint(client, create_user, sync_db)
    longitude, latitude = stored_complaint(sync_db, complaint_id)["location"]["coordinates"]
    response = resolve_with_photo(client, worker, complaint_id, content=geotagged_jpeg(latitude + 0.01, longitude))
    assert response.status_code == 422
    assert "from the reported location" in response.json()["errors"][0]["message"]
    assert stored_complaint(sync_db, complaint_id)["status"] == "IN_PROGRESS"


def test_worker_cannot_resolve_with_the_plain_status_route(client, create_user, sync_db):
    _, worker, complaint_id = started_complaint(client, create_user, sync_db)
    response = client.patch(f"{WORKER_URL}/{complaint_id}/status", json={"status": "RESOLVED"}, headers=worker)
    assert response.status_code == 422
    assert "geotagged" in response.json()["errors"][0]["message"]
    assert stored_complaint(sync_db, complaint_id)["status"] == "IN_PROGRESS"


def test_resolve_needs_the_complaint_to_be_in_progress(client, create_user, sync_db):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    response = resolve_with_photo(client, worker, complaint_id)  # still SUBMITTED
    assert response.status_code == 409
    assert "Cannot change status" in response.json()["message"]


def test_resolve_only_for_workers_of_the_same_department(client, create_user, sync_db):
    _, _, complaint_id = started_complaint(client, create_user, sync_db)
    other = make_worker(create_user, sync_db, email="water@example.com", department_code="WATER_SUPPLY")
    assert resolve_with_photo(client, other, complaint_id).status_code == 404
    citizen = create_user(email="c2@example.com")
    assert resolve_with_photo(client, citizen, complaint_id).status_code == 403
    assert stored_complaint(sync_db, complaint_id)["status"] == "IN_PROGRESS"


def test_resolve_requires_a_photo_file(client, create_user, sync_db):
    _, worker, complaint_id = started_complaint(client, create_user, sync_db)
    assert client.post(f"{WORKER_URL}/{complaint_id}/resolve", data={"note": "done"}, headers=worker).status_code == 422


def test_rejected_resolve_leaves_no_photo_behind(client, create_user, sync_db):
    from pathlib import Path

    _, worker, complaint_id = started_complaint(client, create_user, sync_db)
    folder = Path(settings.upload_dir) / "resolutions"
    before = len(list(folder.iterdir())) if folder.exists() else 0
    resolve_with_photo(client, worker, complaint_id, content=untagged_jpeg())
    after = len(list(folder.iterdir())) if folder.exists() else 0
    assert after == before
