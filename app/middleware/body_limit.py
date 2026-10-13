from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.responses import error_response


class BodyLimitMiddleware(BaseHTTPMiddleware):
    """Refuses oversized request bodies early, using the Content-Length header.

    Photo uploads may be a little bigger than MAX_UPLOAD_MB (the form fields come on top);
    everything else (JSON) must be small. The image service still checks the real photo size.
    """

    async def dispatch(self, request, call_next):
        declared = request.headers.get("content-length")
        if declared is not None:
            if not declared.isdigit():
                return error_response(400, "Invalid Content-Length header")
            is_upload = request.headers.get("content-type", "").startswith("multipart/form-data")
            limit = (settings.max_upload_mb + 1) * 1024 * 1024 if is_upload else settings.max_json_body_kb * 1024
            if int(declared) > limit:
                return error_response(413, "Request body is too large")
        return await call_next(request)
