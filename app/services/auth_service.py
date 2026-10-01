from pymongo.errors import DuplicateKeyError

from app.core.database import get_database
from app.core.errors import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import USERS_COLLECTION, Role, build_user_document
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.user_service import to_public_user


async def register_citizen(data: RegisterRequest) -> dict:
    users = get_database()[USERS_COLLECTION]

    if await users.find_one({"email": data.email}, {"_id": 1}):
        raise ApiError(409, "An account with this email already exists")

    # Role is fixed by the server. Public registration can only create citizens.
    user_document = build_user_document(
        name=data.name,
        email=data.email,
        password_hash=await hash_password(data.password),
        phone=data.phone,
        role=Role.CITIZEN,
    )

    try:
        await users.insert_one(user_document)  # this also adds "_id" to user_document
    except DuplicateKeyError:
        # Two people registered the same email at the same instant: the unique index caught it
        raise ApiError(409, "An account with this email already exists")

    return to_public_user(user_document)


async def login_user(data: LoginRequest) -> dict:
    users = get_database()[USERS_COLLECTION]
    user = await users.find_one({"email": data.email})

    # Same message for "no such email" and "wrong password", so attackers can't tell which emails exist
    if user is None or not await verify_password(data.password, user["passwordHash"]):
        raise ApiError(401, "Invalid email or password")

    if not user["isActive"]:
        raise ApiError(403, "This account has been deactivated")

    return {
        "accessToken": create_access_token(str(user["_id"])),
        "tokenType": "bearer",
        "user": to_public_user(user),
    }