from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile

from app.core.dependencies import require_roles
from app.core.errors import ApiError
from app.core.responses import success_response
from app.models.complaint import ComplaintStatus
from app.models.user import Role
from app.schemas.complaint import StatusUpdateRequest
from app.services import status_service, worker_service

router = APIRouter(prefix="/worker", tags=["Worker"])
worker_only = Depends(require_roles(Role.WORKER))


@router.get("/complaints")
async def list_my_department_complaints(
    status: ComplaintStatus | None = None,
    assigned_to_me: Annotated[bool, Query(alias="assignedToMe")] = False,
    overdue: bool | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    worker: dict = worker_only,
):
    result = await worker_service.list_department_complaints(
        worker=worker, status=status, assigned_to_me=assigned_to_me, overdue=overdue, page=page, limit=limit
    )
    return success_response("Complaints fetched", result)


@router.get("/complaints/{complaint_id}")
async def get_complaint(complaint_id: str, worker: dict = worker_only):
    complaint = await worker_service.get_department_complaint(worker=worker, complaint_id=complaint_id)
    return success_response("Complaint fetched", complaint)


@router.patch("/complaints/{complaint_id}/status")
async def update_status(
    complaint_id: str,
    data: StatusUpdateRequest,
    background_tasks: BackgroundTasks,
    worker: dict = worker_only,
):
    if data.status == ComplaintStatus.RESOLVED:
        raise ApiError(
            422,
            "Validation failed",
            [{"field": "status", "message": "To resolve a complaint, upload a geotagged after-fix photo: "
              "POST /worker/complaints/{id}/resolve"}],
        )
    complaint = await status_service.change_status(
        complaint_id=complaint_id,
        new_status=data.status,
        note=data.note,
        worker=worker,
        background_tasks=background_tasks,
    )
    return success_response("Complaint status updated", complaint)


@router.post("/complaints/{complaint_id}/resolve", summary="Mark RESOLVED with a geotagged after-fix photo")
async def resolve_with_photo(
    complaint_id: str,
    background_tasks: BackgroundTasks,
    photo: Annotated[UploadFile, File()],
    note: Annotated[str | None, Form(max_length=500)] = None,
    worker: dict = worker_only,
):
    complaint = await status_service.resolve_with_photo(
        complaint_id=complaint_id,
        photo=photo,
        note=(note or "").strip() or None,
        worker=worker,
        background_tasks=background_tasks,
    )
    return success_response("Complaint resolved", complaint)
