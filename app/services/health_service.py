import time

from app.core.database import ping_database

_started_at = time.time()


async def get_health_status() -> dict:
    database_ok = await ping_database()
    return {
        "uptimeSeconds": round(time.time() - _started_at),
        "database": "connected" if database_ok else "disconnected",
    }