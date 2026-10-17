# Geotagged photos

The project proposal promises geotagged photos. Two photos are checked:

| Photo | Where | Rule |
|-------|-------|------|
| Report photo | `POST /api/v1/complaints` | Must be a JPEG with GPS, taken within 300 m of the pinned location |
| After-fix photo | `POST /api/v1/worker/complaints/{id}/resolve` | Must be a JPEG with GPS, taken within 300 m of the reported location |

A worker can no longer resolve with `PATCH /worker/complaints/{id}/status`. That route answers 422 and points to `/resolve`.
Admins can still set any status without a photo (an override).

How it works (explainable in a viva):
1. A phone camera writes the position into the photo's EXIF data.
2. `app/services/geotag_service.py` reads latitude and longitude from the JPEG with plain Python (no extra package).
3. The distance to the complaint is worked out with the haversine formula.
4. No GPS, a PNG or WebP file, or a distance over the limit gives a 422 with a message that says what to fix.

Settings in `.env`: `REQUIRE_PHOTO_GPS` (default true) and `GEOTAG_MAX_DISTANCE_METERS` (default 300).

Demo tool: `python scripts/geotag_photo.py set photo.jpg 19.1867 73.1920 out.jpg` writes a position into a JPEG,
and `python scripts/geotag_photo.py show photo.jpg` reads it.

Limits to know: a screenshot or a picture downloaded from the internet has no GPS and is refused.
GPS in a photo can be faked by someone who edits the file; this check stops honest mistakes, not a determined cheat.
