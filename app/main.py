import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings, validate_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.core.errors import register_exception_handlers
from app.core.responses import success_response
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.models.indexes import create_all_indexes
from app.routes import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_settings()           # refuse to start with an unsafe JWT secret
    await connect_to_mongo()
    await create_all_indexes()    # unique indexes, 2dsphere index, etc.
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Civic Issue Reporting and Management System",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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