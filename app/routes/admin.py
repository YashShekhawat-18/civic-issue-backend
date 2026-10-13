from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.database import get_database
from app.core.dependencies import require_roles
from app.core.responses import success_response
from app.models.audit_log import AuditAction
from app.models.complaint import ACTIVE_STATUSES, COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.user import Role
from app.services import admin_service, audit_service, catalog_admin_service, overdue_service, statistics_service

router = APIRouter(prefix="/admin", tags=["Admin"], dependencies=[Depends(require_roles(Role.ADMIN))])


@router.get("/dashboard", summary="Dashboard: statistics plus the oldest overdue complaints")
async def dashboard():
    return success_response("Dashboard fetched", await statistics_service.get_dashboard())


@router.get("/statistics", summary="Totals, and complaints by status, category and department")
async def statistics():
    return success_response("Statistics fetched", await statistics_service.get_statistics())


# ---------- complaints ----------
# "/complaints/map" must stay ABOVE "/complaints/{complaint_id}", otherwise "map" would be read as an id.

@router.get("/complaints", summary="All complaints, with filters")
async def list_complaints(
    status: ComplaintStatus | None = None,
    category_id: Annotated[str | None, Query(alias="categoryId")] = None,
    department_id: Annotated[str | None, Query(alias="departmentId")] = None,
    overdue: bool | None = None,
    number: Annotated[str | None, Query(description="Exact complaint number, e.g. CIV-2026-000001", max_length=30)] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
):
    result = await admin_service.list_complaints(
        status=status, category_id=category_id, department_id=department_id,
        overdue=overdue, number=number, page=page, limit=limit,
    )
    return success_response("Complaints fetched", result)


@router.get("/complaints/map", summary="All complaints as map pins")
async def complaints_for_map(
    status: ComplaintStatus | None = None,
    category_id: Annotated[str | None, Query(alias="categoryId")] = None,
    department_id: Annotated[str | None, Query(alias="departmentId")] = None,
    overdue: bool | None = None,
    limit: int = Query(admin_service.MAP_DEFAULT_LIMIT, ge=1, le=1000),
):
    result = await admin_service.list_for_map(
        status=status, category_id=category_id, department_id=department_id, overdue=overdue, limit=limit
    )
    return success_response("Map data fetched", result)


@router.get("/complaints/{complaint_id}", summary="One complaint, full detail")
async def get_complaint(complaint_id: str):
    return success_response("Complaint fetched", await admin_service.get_complaint(complaint_id))


# ---------- overdue ----------

@router.get("/overdue", summary="Open complaints past the overdue limit, oldest first")
async def list_overdue_complaints(page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=50)):
    db = get_database()
    query = {"overdue": True, "status": {"$in": ACTIVE_STATUSES}}
    collection = db[COMPLAINTS_COLLECTION]
    total = await collection.count_documents(query)
    complaints = await collection.find(query).sort("createdAt", 1).skip((page - 1) * limit).limit(limit).to_list()

    items = await admin_service.to_admin_views(db, complaints)
    now = datetime.now(timezone.utc)
    for item, complaint in zip(items, complaints):
        item["ageDays"] = (now - complaint["createdAt"]).days
    return success_response("Overdue complaints fetched", {"items": items, "page": page, "limit": limit, "total": total})


@router.post("/overdue/check", summary="Run the overdue check now")
async def run_overdue_check_now():
    return success_response("Overdue check finished", await overdue_service.mark_overdue_complaints())


# ---------- audit log ----------

@router.get("/audit-logs", summary="Who did what, newest first")
async def audit_logs(
    action: AuditAction | None = None,
    entity: Annotated[str | None, Query(max_length=30, description="COMPLAINT, DEPARTMENT, CATEGORY or USER")] = None,
    user_id: Annotated[str | None, Query(alias="userId")] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    result = await audit_service.list_audit_logs(action=action, entity=entity, user_id=user_id, page=page, limit=limit)
    return success_response("Audit logs fetched", result)


# ---------- lists that include inactive records (the public lists show only active ones) ----------

@router.get("/departments", summary="All departments, including inactive ones")
async def all_departments():
    return success_response("Departments fetched", await catalog_admin_service.list_all_departments())


@router.get("/categories", summary="All categories, including inactive ones")
async def all_categories():
    return success_response("Categories fetched", await catalog_admin_service.list_all_categories())
