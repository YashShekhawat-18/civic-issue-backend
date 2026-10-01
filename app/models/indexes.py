from app.core.database import get_database
from app.models.user import create_user_indexes


async def create_all_indexes() -> None:
    db = get_database()
    await create_user_indexes(db)