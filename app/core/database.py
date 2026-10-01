from pymongo import AsyncMongoClient

from app.core.config import settings

client: AsyncMongoClient | None = None


async def connect_to_mongo() -> None:
    """Create the MongoDB client. Called once when the app starts."""
    global client
    client = AsyncMongoClient(settings.mongo_uri, serverSelectionTimeoutMS=3000, tz_aware=True)

    # In tests the first real database call connects, so no ping is needed here
    if settings.app_env != "test":
        await client.admin.command("ping")  # fail fast if MongoDB is not reachable
        print("MongoDB connected")  # we never print the URI: it may contain a password


async def close_mongo_connection() -> None:
    """Called once when the app shuts down."""
    if client is not None:
        await client.close()


def get_database():
    """Return the database object used by the services."""
    return client[settings.mongo_db_name]


async def ping_database() -> bool:
    """Used by the health check. Returns True if MongoDB answers."""
    if client is None:
        return False
    try:
        await client.admin.command("ping")
        return True
    except Exception:
        return False