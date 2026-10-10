from fastapi import APIRouter

from app.routes import admin, auth, categories, complaints, departments, gamification, health, notifications, worker

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(departments.router)
api_router.include_router(categories.router)
api_router.include_router(complaints.router)
api_router.include_router(worker.router)
api_router.include_router(notifications.router)
api_router.include_router(gamification.router)
api_router.include_router(admin.router)
