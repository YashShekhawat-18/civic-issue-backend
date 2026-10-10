from fastapi import APIRouter, Depends, Query

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.services import notification_service

# Every logged-in user (citizen, worker, admin) has their own notifications.
router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def list_my_notifications(
    unread_only: bool = Query(False, alias="unreadOnly"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    result = await notification_service.list_notifications(
        user=current_user, unread_only=unread_only, page=page, limit=limit
    )
    return success_response("Notifications fetched", result)


# Must stay ABOVE "/{notification_id}/read" so "read-all" is not mistaken for an id.
@router.patch("/read-all")
async def mark_all_read(current_user: dict = Depends(get_current_user)):
    result = await notification_service.mark_all_as_read(user=current_user)
    return success_response("All notifications marked as read", result)


@router.patch("/{notification_id}/read")
async def mark_read(notification_id: str, current_user: dict = Depends(get_current_user)):
    notification = await notification_service.mark_as_read(user=current_user, notification_id=notification_id)
    return success_response("Notification marked as read", notification)
