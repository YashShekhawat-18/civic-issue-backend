from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.core.dependencies import require_roles
from app.core.responses import success_response
from app.models.complaint import ComplaintStatus
from app.models.user import Role
from app.services import complaint_service, upvote_service

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
    created, data = await complaint_service.create_complaint(
        reporter=current_user,
        title=title,
        description=description,
        category_id=category_id,
        latitude=latitude,
        longitude=longitude,
        is_anonymous=is_anonymous,
        photo=photo,
    )
    if created:
        return success_response("Complaint submitted", data, status_code=201)
    # A similar complaint already exists nearby: nothing was created (status 200, not 201)
    return success_response(data["message"], data)


# This route must stay ABOVE "/{complaint_id}", otherwise "nearby" would be read as an id.
@router.get("/nearby")
async def nearby_complaints(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    radius: Annotated[int, Query(ge=10, le=5000, description="Search radius in metres")] = 500,
    category_id: Annotated[str | None, Query(alias="categoryId")] = None,
    current_user: dict = Depends(require_roles(Role.CITIZEN)),
):
    result = await complaint_service.list_nearby_complaints(
        viewer=current_user,
        latitude=latitude,
        longitude=longitude,
        radius_meters=radius,
        category_id=category_id,
    )
    return success_response("Nearby complaints fetched", result)


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


@router.post("/{complaint_id}/upvote", status_code=201)
async def upvote_complaint(
    complaint_id: str,
    current_user: dict = Depends(require_roles(Role.CITIZEN)),
):
    result = await upvote_service.add_upvote(complaint_id, current_user["_id"])
    return success_response("Upvote added", result, status_code=201)


@router.delete("/{complaint_id}/upvote")
async def remove_upvote(
    complaint_id: str,
    current_user: dict = Depends(require_roles(Role.CITIZEN)),
):
    result = await upvote_service.remove_upvote(complaint_id, current_user["_id"])
    return success_response("Upvote removed", result)
