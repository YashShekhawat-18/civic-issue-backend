"""A logged-in user managing their own account."""
from datetime import datetime, timezone

from pymongo import ReturnDocument

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.security import hash_password, verify_password
from app.models.audit_log import AuditAction
from app.models.user import USERS_COLLECTION
from app.schemas.admin import ChangePasswordRequest, ProfileUpdate
from app.services import audit_service
from app.services.user_service import to_public_user


async def update_profile(*, user: dict, data: ProfileUpdate) -> dict:
    """Only name and phone can be changed. The user id always comes from the login token."""
    updates: dict = {}
    if "name" in data.model_fields_set and data.name is not None:
        updates["name"] = data.name
    if "phone" in data.model_fields_set:
        updates["phone"] = data.phone
    if not updates:
        return to_public_user(user)

    updates["updatedAt"] = datetime.now(timezone.utc)
    updated = await get_database()[USERS_COLLECTION].find_one_and_update(
        {"_id": user["_id"]}, {"$set": updates}, return_document=ReturnDocument.AFTER
    )
    await audit_service.log_action(
        actor=user, action=AuditAction.PROFILE_UPDATED, entity="USER", entity_id=user["_id"],
        metadata={"fields": sorted(k for k in updates if k != "updatedAt")},
    )
    return to_public_user(updated)


async def change_password(*, user: dict, data: ChangePasswordRequest) -> None:
    if not await verify_password(data.current_password, user["passwordHash"]):
        raise ApiError(400, "Current password is incorrect")
    if data.current_password == data.new_password:
        raise ApiError(422, "Validation failed", [{"field": "newPassword", "message": "New password must be different from the current one"}])

    await get_database()[USERS_COLLECTION].update_one(
        {"_id": user["_id"]},
        {"$set": {"passwordHash": await hash_password(data.new_password), "updatedAt": datetime.now(timezone.utc)}},
    )
    await audit_service.log_action(actor=user, action=AuditAction.PASSWORD_CHANGED, entity="USER", entity_id=user["_id"])
