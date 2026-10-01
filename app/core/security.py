import asyncio
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.errors import ApiError


def _hash_sync(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_sync(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# bcrypt is deliberately slow. We run it in a separate thread so the server
# can keep answering other requests while it works.
async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_sync, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(_verify_sync, password, password_hash)


def create_access_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,  # "subject": who this token belongs to
        "iat": now,      # issued at
        "exp": now + timedelta(minutes=settings.jwt_expires_minutes),  # expires at
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> str:
    """Returns the user id inside the token, or raises a 401 error."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "Token has expired. Please log in again")
    except jwt.InvalidTokenError:
        raise ApiError(401, "Invalid authentication token")
    return payload["sub"]