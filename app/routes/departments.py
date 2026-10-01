from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.core.responses import success_response
from app.services import department_service

router = APIRouter(
    prefix="/departments", tags=["Departments"], dependencies=[Depends(get_current_user)]
)


@router.get("")
async def list_departments():
    departments = await department_service.list_active_departments()
    return success_response("Departments fetched", departments)


@router.get("/{department_id}")
async def get_department(department_id: str):
    department = await department_service.get_department_or_404(department_id)
    return success_response("Department fetched", department_service.to_public_department(department))