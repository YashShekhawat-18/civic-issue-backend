from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"   # stop MIME sniffing
        response.headers["X-Frame-Options"] = "DENY"             # stop clickjacking
        response.headers["Referrer-Policy"] = "no-referrer"
        return response