from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.dependencies import require_roles
from app.core.responses import success_response
from app.models.complaint import ComplaintStatus
from app.models.user import Role
from app.services import complaint_service

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.post("", status_code=201)
async def create_complaint(
    title: Annotated[str, Form(min_length=5, max_length=150)],
    description: Annotated[str, Form(min_length=10, max_length=2000)],
    category_id: Annotated[str, Form(alias="categoryId")],
    latitude: Annotated[float, Form(ge=-90, le=90)],
    longitude: Annotated[float, Form(ge=-180, le=180)],
    photo: Annotated[UploadFile, File()],
    is_anonymous: Annotated[bool, Form(alias="isAnonymous")] = False,
    current_user: dict = Depends(require_roles(Role.CITIZEN)),
):
    complaint = await complaint_service.create_complaint(
        reporter=current_user,
        title=title,
        description=description,
        category_id=category_id,
        latitude=latitude,
        longitude=longitude,
        is_anonymous=is_anonymous,
        photo=photo,
    )
    return success_response("Complaint submitted", complaint, status_code=201)


@router.get("")
async def list_complaints(
    status: ComplaintStatus | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: dict = Depends(require_roles(Role.CITIZEN, Role.ADMIN)),
):
    result = await complaint_service.list_complaints(
        user=current_user, status=status, page=page, limit=limit
    )
    return success_response("Complaints fetched", result)


@router.get("/{complaint_id}")
async def get_complaint(
    complaint_id: str,
    current_user: dict = Depends(require_roles(Role.CITIZEN, Role.ADMIN)),
):
    complaint = await complaint_service.get_complaint_for_user(complaint_id, current_user)
    return success_response("Complaint fetched", complaint)
