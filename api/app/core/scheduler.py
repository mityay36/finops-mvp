import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.jobs import allocations_snapshot, billing_sync   # ← добавлен allocations_snapshot


logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="UTC")
    return _scheduler


def start_scheduler() -> None:
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled by config; skipping start")
        return
    scheduler = get_scheduler()
    if scheduler.running:
        return

    scheduler.add_job(
        billing_sync.sync_all_active_yc_clusters,
        trigger="interval",
        minutes=settings.billing_sync_interval_minutes,
        id="billing_sync",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=None,
    )

    scheduler.add_job(
        allocations_snapshot.snapshot_all_active_clusters,
        trigger="interval",
        minutes=settings.allocations_snapshot_interval_minutes,
        id="allocations_snapshot",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=None,
        jitter=60,  # spread retry-storms if multiple instances ever exist
    )

    scheduler.start()
    logger.info("APScheduler started")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
    _scheduler = None
