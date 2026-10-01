from fastapi import APIRouter

from app.core.responses import success_response
from app.services import health_service

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def get_health():
    data = await health_service.get_health_status()
    return success_response("Server is running", data)