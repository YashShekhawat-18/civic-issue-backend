import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.responses import error_response

logger = logging.getLogger("civic")


class ApiError(Exception):
    """Raise this anywhere: raise ApiError(404, "Complaint not found")"""

    def __init__(self, status_code: int, message: str, errors: list | None = None):
        self.status_code = status_code
        self.message = message
        self.errors = errors or []


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, exc: ApiError):
        return error_response(exc.status_code, exc.message, exc.errors)

    # Covers unknown URLs (404), wrong method (405), etc.
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        return error_response(exc.status_code, str(exc.detail))

    # Request body / query failed Pydantic validation
    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(part) for part in err["loc"] if part != "body"),
                "message": err["msg"].removeprefix("Value error, "),
            }
            for err in exc.errors()
        ]
        return error_response(422, "Validation failed", errors)

    # Anything unexpected: log details on the server, send a safe message to the client
    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.exception("Unhandled error")
        return error_response(500, "Internal server error")