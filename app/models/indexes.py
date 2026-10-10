from app.core.database import get_database
from app.models.badge import create_badge_indexes
from app.models.category import create_category_indexes
from app.models.complaint import create_complaint_indexes
from app.models.department import create_department_indexes
from app.models.notification import create_notification_indexes
from app.models.upvote import create_upvote_indexes
from app.models.user import create_user_indexes


async def create_all_indexes(db=None) -> None:
    if db is None:
        db = get_database()
    await create_user_indexes(db)
    await create_department_indexes(db)
    await create_category_indexes(db)
    await create_badge_indexes(db)
    await create_complaint_indexes(db)
    await create_upvote_indexes(db)
    await create_notification_indexes(db)
