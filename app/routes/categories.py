from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.services import category_service

router = APIRouter(
    prefix="/categories", tags=["Categories"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def list_categories():
    categories = await category_service.list_active_categories()
    return success_response("Categories fetched", categories)
