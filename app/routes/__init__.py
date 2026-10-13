from fastapi import APIRouter

from app.routes import (
    admin,
    admin_workers,
    auth,
    catalog_admin,
    categories,
    complaints,
    complaints_admin,
    departments,
    gamification,
    health,
    notifications,
    profile,
    worker,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(profile.router)
# Every (method, URL) pair must be defined only once (tests/test_route_matrix.py checks this).
# GET /departments/{id} and GET /categories/{id} live in catalog_admin (admins can see inactive items).
api_router.include_router(catalog_admin.categories_router)
api_router.include_router(departments.router)
api_router.include_router(catalog_admin.departments_router)
api_router.include_router(categories.router)
api_router.include_router(complaints.router)
api_router.include_router(complaints_admin.router)
api_router.include_router(worker.router)
api_router.include_router(notifications.router)
api_router.include_router(gamification.router)
api_router.include_router(admin.router)
api_router.include_router(admin_workers.router)
