from app.core.config import settings
from app.models.complaint import ACTIVE_STATUSES, COMPLAINTS_COLLECTION


async def find_nearby_complaints(
    db, *, latitude: float, longitude: float, radius_meters: int, query: dict | None = None, limit: int = 50
) -> list[dict]:
    """Complaints within radius_meters of a point, nearest first.

    Each result has an extra "distanceMeters" field. $geoNear uses the 2dsphere index.
    """
    pipeline = [
        {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [longitude, latitude]},  # [longitude, latitude]
                "distanceField": "distanceMeters",
                "maxDistance": radius_meters,  # metres, because "near" is a GeoJSON point
                "spherical": True,
                "query": query or {},
            }
        },
        {"$limit": limit},
    ]
    cursor = await db[COMPLAINTS_COLLECTION].aggregate(pipeline)
    return await cursor.to_list()


async def find_nearby_duplicate(db, *, category_id, latitude: float, longitude: float) -> dict | None:
    """The nearest ACTIVE complaint of the SAME category inside DUPLICATE_RADIUS_METERS, or None."""
    matches = await find_nearby_complaints(
        db,
        latitude=latitude,
        longitude=longitude,
        radius_meters=settings.duplicate_radius_meters,
        query={"categoryId": category_id, "status": {"$in": ACTIVE_STATUSES}},
        limit=1,
    )
    return matches[0] if matches else None
