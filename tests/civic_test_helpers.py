"""Small helpers shared by the complaint, duplicate and upvote tests."""

COMPLAINTS_URL = "/api/v1/complaints"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"fake-image-data"  # starts like a real PNG

BASE_LATITUDE = 19.1867
BASE_LONGITUDE = 73.1920
METERS_PER_DEGREE_LATITUDE = 111_320


def category_id(sync_db, code):
    return str(sync_db["categories"].find_one({"code": code})["_id"])


def latitude_for(spot=0, meters_north=0):
    """spot=1 is about 1.1 km north of spot=0, far outside the 100 m duplicate radius."""
    return BASE_LATITUDE + spot * 0.01 + meters_north / METERS_PER_DEGREE_LATITUDE


def complaint_form(sync_db, code="POTHOLE", spot=0, meters_north=0, **changes):
    form = {
        "title": "Big pothole near the school",
        "description": "A deep pothole is blocking the left lane.",
        "categoryId": category_id(sync_db, code),
        "latitude": f"{latitude_for(spot, meters_north):.6f}",
        "longitude": f"{BASE_LONGITUDE:.6f}",
    }
    form.update(changes)
    return form


def post_complaint(client, headers, form, filename="pothole.png", content=PNG_BYTES, content_type="image/png"):
    return client.post(
        COMPLAINTS_URL,
        data=form,
        files={"photo": (filename, content, content_type)},
        headers=headers,
    )


def user_id(client, headers):
    return client.get("/api/v1/auth/me", headers=headers).json()["data"]["id"]
