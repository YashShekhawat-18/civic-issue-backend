from fastapi import APIRouter

from app.routes import auth, categories, complaints, departments, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(departments.router)
api_router.include_router(categories.router)
api_router.include_router(complaints.router)
