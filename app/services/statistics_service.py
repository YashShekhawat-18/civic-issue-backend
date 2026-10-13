"""Numbers for the admin dashboard. Everything is counted by MongoDB, not in Python."""
from datetime import datetime, timezone

from app.core.database import get_database
from app.models.category import CATEGORIES_COLLECTION
from app.models.complaint import ACTIVE_STATUSES, COMPLAINTS_COLLECTION, ComplaintStatus
from app.models.department import DEPARTMENTS_COLLECTION
from app.services import admin_service

RECENT_LIMIT = 10
OVERDUE_PREVIEW_LIMIT = 5


async def _count_by(db, field: str) -> dict:
    rows = await db[COMPLAINTS_COLLECTION].aggregate([{"$group": {"_id": f"${field}", "count": {"$sum": 1}}}])
    return {row["_id"]: row["count"] for row in await rows.to_list()}


async def get_statistics() -> dict:
    db = get_database()
    complaints = db[COMPLAINTS_COLLECTION]

    by_status = await _count_by(db, "status")
    total = sum(by_status.values())
    resolved = by_status.get(ComplaintStatus.RESOLVED.value, 0)
    overdue = await complaints.count_documents({"overdue": True, "status": {"$in": ACTIVE_STATUSES}})

    by_category_counts = await _count_by(db, "categoryId")
    by_department_counts = await _count_by(db, "departmentId")
    categories = {c["_id"]: c for c in await db[CATEGORIES_COLLECTION].find({"_id": {"$in": list(by_category_counts)}}).to_list()}
    departments = {d["_id"]: d for d in await db[DEPARTMENTS_COLLECTION].find({"_id": {"$in": list(by_department_counts)}}).to_list()}

    def named(counts: dict, lookup: dict) -> list[dict]:
        rows = [
            {
                "id": str(item_id),
                "name": lookup[item_id]["name"] if item_id in lookup else "(deleted)",
                "code": lookup[item_id]["code"] if item_id in lookup else None,
                "count": count,
            }
            for item_id, count in counts.items()
        ]
        return sorted(rows, key=lambda r: (-r["count"], r["name"]))

    recent = await complaints.find({}).sort("createdAt", -1).limit(RECENT_LIMIT).to_list()

    return {
        "totals": {
            "total": total,
            "submitted": by_status.get(ComplaintStatus.SUBMITTED.value, 0),
            "inProgress": by_status.get(ComplaintStatus.IN_PROGRESS.value, 0),
            "resolved": resolved,
            "overdue": overdue,
        },
        "resolutionRatePercent": round(resolved * 100 / total, 1) if total else 0.0,
        "byStatus": [{"status": s.value, "count": by_status.get(s.value, 0)} for s in ComplaintStatus],
        "byCategory": named(by_category_counts, categories),
        "byDepartment": named(by_department_counts, departments),
        "recentComplaints": await admin_service.to_admin_views(db, recent),
    }


async def get_dashboard() -> dict:
    """Everything in get_statistics() plus the oldest overdue complaints, in one request."""
    db = get_database()
    data = await get_statistics()
    oldest_overdue = (
        await db[COMPLAINTS_COLLECTION]
        .find({"overdue": True, "status": {"$in": ACTIVE_STATUSES}})
        .sort("createdAt", 1)
        .limit(OVERDUE_PREVIEW_LIMIT)
        .to_list()
    )
    views = await admin_service.to_admin_views(db, oldest_overdue)
    now = datetime.now(timezone.utc)
    for view, complaint in zip(views, oldest_overdue):
        view["ageDays"] = (now - complaint["createdAt"]).days
    data["oldestOverdue"] = views
    return data
