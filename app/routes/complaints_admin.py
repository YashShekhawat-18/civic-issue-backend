"""Admin-only actions on a complaint. The citizen routes stay in routes/complaints.py."""
from fastapi import APIRouter, BackgroundTasks, Depends

from app.core.dependencies import require_roles
from app.core.responses import success_response
from app.models.user import Role
from app.schemas.admin import ComplaintUpdate
from app.schemas.complaint import StatusUpdateRequest
from app.services import admin_service, status_service

router = APIRouter(prefix="/complaints", tags=["Complaints"])


@router.patch("/{complaint_id}", summary="Edit a complaint (admin)")
async def update_complaint(complaint_id: str, data: ComplaintUpdate, admin: dict = Depends(require_roles(Role.ADMIN))):
    complaint = await admin_service.update_complaint(actor=admin, complaint_id=complaint_id, data=data)
    return success_response("Complaint updated", complaint)


@router.delete("/{complaint_id}", summary="Delete a complaint (admin)")
async def delete_complaint(complaint_id: str, admin: dict = Depends(require_roles(Role.ADMIN))):
    return success_response("Complaint deleted", await admin_service.delete_complaint(actor=admin, complaint_id=complaint_id))


@router.patch("/{complaint_id}/status", summary="Change the status of any complaint (admin)")
async def update_status(
    complaint_id: str,
    data: StatusUpdateRequest,
    background_tasks: BackgroundTasks,
    admin: dict = Depends(require_roles(Role.ADMIN)),
):
    await status_service.change_status(
        complaint_id=complaint_id, new_status=data.status, note=data.note, worker=admin, background_tasks=background_tasks
    )
    return success_response("Complaint status updated", await admin_service.get_complaint(complaint_id))
