import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, validate_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.errors import register_exception_handlers
from app.core.responses import success_response
from app.jobs.scheduler import start_scheduler, stop_scheduler
from app.middleware.body_limit import BodyLimitMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.indexes import create_all_indexes
from app.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()           # refuse to start with an unsafe JWT secret
    await connect_to_mongo()
    await create_all_indexes()    # unique indexes, 2dsphere index, etc.
    start_scheduler()             # overdue check runs in the background
    yield
    stop_scheduler()
    await close_mongo_connection()


DESCRIPTION = """
Citizens report civic issues (with a photo and a map location), workers fix them, admins manage everything.

**How to try it in this page:** register or log in (`/api/v1/auth/login`), copy the `accessToken`,
click the **Authorize** button and paste it. Every response has the shape
`{"success": true, "message": "...", "data": {...}}` or `{"success": false, "message": "...", "errors": []}`.
"""

TAGS_METADATA = [
    {"name": "Health", "description": "Is the server (and database) running?"},
    {"name": "Auth", "description": "Register, log in, who am I."},
    {"name": "Profile", "description": "Change my own name, phone and password."},
    {"name": "Departments", "description": "Departments (database-driven). Admins can create, edit and deactivate."},
    {"name": "Categories", "description": "The 15 issue categories and the department each one belongs to."},
    {"name": "Complaints", "description": "Report, view, upvote. Admins can edit, delete and change status."},
    {"name": "Worker", "description": "Worker portal: complaints of my own department and status changes."},
    {"name": "Notifications", "description": "In-app notifications for every user."},
    {"name": "Points and Badges", "description": "My points and badges, all badges, leaderboard."},
    {"name": "Admin", "description": "Dashboard, statistics, all complaints, map, overdue, audit logs."},
    {"name": "Admin - Workers", "description": "Create and manage worker accounts."},
]

app = FastAPI(
    title="Civic Issue Reporting and Management System",
    version="1.0.0",
    description=DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    # Swagger remembers the token after a page refresh (handy while testing)
    swagger_ui_parameters={"persistAuthorization": True},
)

# The LAST middleware added is the OUTERMOST one (it sees the request first).
# Order, outside to inside: security headers -> CORS -> rate limit -> body size limit -> routes.
# That way even a 429 or 413 answer carries the security and CORS headers.
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

register_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")

# Uploaded photos are served from /uploads/...
os.makedirs(settings.upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


@app.get("/", include_in_schema=False)
async def root():
    return success_response(
        "Civic Issue Reporting API is running",
        {"docs": "/docs", "health": "/api/v1/health"},
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)  # the browser asks for a tab icon; we have none
