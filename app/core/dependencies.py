from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.models.user import Role
from app.services import user_service

# auto_error=False lets us return our own standard JSON error instead of FastAPI's default
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise ApiError(401, "Authentication required")

    user_id = decode_access_token(credentials.credentials)
    user = await user_service.get_user_by_id(user_id)

    if user is None or not user["isActive"]:
        raise ApiError(401, "User does not exist or is deactivated")
    return user


def require_roles(*allowed_roles: Role):
    """Usage in a route: Depends(require_roles(Role.ADMIN))"""
    allowed_values = [role.value for role in allowed_roles]

    async def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in allowed_values:
            raise ApiError(403, "You do not have permission to perform this action")
        return current_user

    return role_checker