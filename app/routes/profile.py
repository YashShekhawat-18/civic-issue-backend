from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.schemas.admin import ChangePasswordRequest, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/users/me", tags=["Profile"])


@router.patch("", summary="Change my name or phone number")
async def update_my_profile(data: ProfileUpdate, current_user: dict = Depends(get_current_user)):
    return success_response("Profile updated", await profile_service.update_profile(user=current_user, data=data))


@router.post("/change-password", summary="Change my password")
async def change_my_password(data: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    await profile_service.change_password(user=current_user, data=data)
    return success_response("Password changed")
