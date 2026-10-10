"""Runs background jobs while the server is running (the Python version of node-cron)."""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.services import overdue_service

logger = logging.getLogger("uvicorn.error")
OVERDUE_JOB_ID = "overdue-check"

scheduler: AsyncIOScheduler | None = None


async def run_overdue_check() -> None:
    """The job itself. A crash here is logged and must never stop the scheduler."""
    try:
        await overdue_service.mark_overdue_complaints()
    except Exception:
        logger.exception("Overdue check failed")


def build_scheduler() -> AsyncIOScheduler:
    new_scheduler = AsyncIOScheduler(timezone="UTC")
    new_scheduler.add_job(
        run_overdue_check,
        trigger=IntervalTrigger(minutes=settings.overdue_check_minutes),
        id=OVERDUE_JOB_ID,
        next_run_time=datetime.now(timezone.utc),  # also run once right at start-up
        max_instances=1,   # never two checks at the same time
        coalesce=True,     # if the server was busy, run once, not once per missed slot
        replace_existing=True,
    )
    return new_scheduler


def start_scheduler() -> None:
    global scheduler
    if not settings.scheduler_enabled or settings.app_env == "test":
        return
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("Scheduler started: overdue check every %s minute(s)", settings.overdue_check_minutes)


def stop_scheduler() -> None:
    global scheduler
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        scheduler = None
