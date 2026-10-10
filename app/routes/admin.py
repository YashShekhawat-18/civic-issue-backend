from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.core.database import get_database
from app.core.dependencies import require_roles
from app.core.responses import success_response
from app.models.complaint import ACTIVE_STATUSES, COMPLAINTS_COLLECTION
from app.models.user import Role
from app.services import overdue_service, worker_service

router = APIRouter(prefix="/admin", tags=["Admin"])
admin_only = Depends(require_roles(Role.ADMIN))


@router.get("/overdue")
async def list_overdue_complaints(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    admin: dict = admin_only,
):
    """Complaints that are still open and past the overdue limit. The oldest come first."""
    db = get_database()
    query = {"overdue": True, "status": {"$in": ACTIVE_STATUSES}}
    collection = db[COMPLAINTS_COLLECTION]
    total = await collection.count_documents(query)
    cursor = collection.find(query).sort("createdAt", 1).skip((page - 1) * limit).limit(limit)
    complaints = await cursor.to_list()

    items = await worker_service.to_worker_views(db, complaints)
    now = datetime.now(timezone.utc)
    for item, complaint in zip(items, complaints):
        item["ageDays"] = (now - complaint["createdAt"]).days
    return success_response("Overdue complaints fetched", {"items": items, "page": page, "limit": limit, "total": total})


@router.post("/overdue/check")
async def run_overdue_check_now(admin: dict = admin_only):
    """Runs the overdue check immediately instead of waiting for the schedule (handy for demos)."""
    result = await overdue_service.mark_overdue_complaints()
    return success_response("Overdue check finished", result)
