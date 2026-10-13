from starlette.middleware.base import BaseHTTPMiddleware

# The API only returns JSON, so a browser never needs to run anything from its responses.
API_CSP = "default-src 'none'; frame-ancestors 'none'"
# Uploaded photos are shown as images only. "sandbox" blocks scripts even if a file is mis-detected.
UPLOADS_CSP = "default-src 'none'; img-src 'self'; sandbox"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        path = request.url.path

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        if path.startswith("/api/"):
            response.headers["Content-Security-Policy"] = API_CSP
            response.headers["Cache-Control"] = "no-store"  # never cache tokens or personal data
        elif path.startswith("/uploads/"):
            response.headers["Content-Security-Policy"] = UPLOADS_CSP
        # /docs (Swagger) needs inline scripts, so it gets no CSP.
        return response
