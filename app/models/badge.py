BADGES_COLLECTION = "badges"


def build_badge_document(*, name: str, description: str, icon: str, points_required: int) -> dict:
    return {
        "name": name,
        "description": description,
        "icon": icon,
        "pointsRequired": points_required,
        "isActive": True,
    }


async def create_badge_indexes(db) -> None:
    await db[BADGES_COLLECTION].create_index("name", unique=True)