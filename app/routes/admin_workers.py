from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import require_roles
from app.core.responses import success_response
from app.models.user import Role
from app.schemas.admin import WorkerCreate, WorkerUpdate
from app.services import worker_admin_service

router = APIRouter(prefix="/admin/workers", tags=["Admin - Workers"])


@router.post("", status_code=201, summary="Create a worker account")
async def create_worker(data: WorkerCreate, admin: dict = Depends(require_roles(Role.ADMIN))):
    worker = await worker_admin_service.create_worker(actor=admin, data=data)
    return success_response("Worker created", worker, status_code=201)


@router.get("", summary="List workers")
async def list_workers(
    department_id: Annotated[str | None, Query(alias="departmentId")] = None,
    is_active: Annotated[bool | None, Query(alias="isActive")] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    admin: dict = Depends(require_roles(Role.ADMIN)),
):
    result = await worker_admin_service.list_workers(department_id=department_id, is_active=is_active, page=page, limit=limit)
    return success_response("Workers fetched", result)


@router.get("/{worker_id}", summary="One worker")
async def get_worker(worker_id: str, admin: dict = Depends(require_roles(Role.ADMIN))):
    return success_response("Worker fetched", await worker_admin_service.get_worker(worker_id))


@router.patch("/{worker_id}", summary="Edit a worker, move to another department, (de)activate, reset password")
async def update_worker(worker_id: str, data: WorkerUpdate, admin: dict = Depends(require_roles(Role.ADMIN))):
    worker = await worker_admin_service.update_worker(actor=admin, worker_id=worker_id, data=data)
    return success_response("Worker updated", worker)


@router.delete("/{worker_id}", summary="Deactivate a worker (the account is kept)")
async def deactivate_worker(worker_id: str, admin: dict = Depends(require_roles(Role.ADMIN))):
    worker = await worker_admin_service.deactivate_worker(actor=admin, worker_id=worker_id)
    return success_response("Worker deactivated", worker)
