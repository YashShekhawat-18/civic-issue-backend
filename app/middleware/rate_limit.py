from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.responses import error_response

API_PREFIX = "/api/v1"


def _client_ip(request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _limits() -> dict:
    """(method, path) -> how many attempts are allowed per window. Read at request time."""
    return {
        ("POST", f"{API_PREFIX}/auth/login"): settings.rate_limit_login_max,
        ("POST", f"{API_PREFIX}/auth/register"): settings.rate_limit_register_max,
    }


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Slows down password guessing and fake sign-ups. Only the auth endpoints are limited."""

    async def dispatch(self, request, call_next):
        enabled = settings.rate_limit_enabled and settings.app_env != "test"  # tests log in hundreds of times
        limit = _limits().get((request.method, request.url.path.rstrip("/")))
        if enabled and limit is not None:
            allowed, retry_after = limiter.check(
                f"{request.url.path}:{_client_ip(request)}", limit, settings.rate_limit_window_seconds
            )
            if not allowed:
                response = error_response(429, "Too many attempts. Please wait a while and try again")
                response.headers["Retry-After"] = str(retry_after)
                return response
        return await call_next(request)
