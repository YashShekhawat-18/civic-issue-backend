from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services import auth_service
from app.services.user_service import to_public_user

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201)
async def register(data: RegisterRequest):
    user = await auth_service.register_citizen(data)
    return success_response("Registration successful", user, status_code=201)


@router.post("/login")
async def login(data: LoginRequest):
    result = await auth_service.login_user(data)
    return success_response("Login successful", result)


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return success_response("Current user fetched", to_public_user(current_user))