from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

COUNTERS_COLLECTION = "counters"


async def next_sequence(db, name: str) -> int:
    """Returns 1, 2, 3, ... for the given counter name. Safe when many requests run at once."""
    for _ in range(3):
        try:
            counter = await db[COUNTERS_COLLECTION].find_one_and_update(
                {"_id": name},
                {"$inc": {"seq": 1}},
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
            return counter["seq"]
        except DuplicateKeyError:
            # Two requests created the very first counter at the same instant. Try again.
            continue
    raise RuntimeError("Could not generate the next sequence number")
