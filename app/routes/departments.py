from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.services import department_service

router = APIRouter(prefix="/departments", tags=["Departments"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_departments():
    return success_response("Departments fetched", await department_service.list_active_departments())

# GET /departments/{id} lives in catalog_admin.py (admins may also see inactive departments).
# It must exist exactly once: two routes with the same method + URL are resolved by registration
# order, and that is easy to get wrong.
