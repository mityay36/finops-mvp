"""Allocations snapshot service.

Mirrors BillingSyncService:
- reserve_run() inside a request session, commits immediately to make the
  RUNNING row visible to other transactions.
- execute_run() runs in its own AsyncSession (called from BackgroundTask /
  APScheduler job).

Hourly job triggers incremental sync. Manual backfill triggered via dedicated
endpoint with explicit days parameter.
"""

from __future__ import annotations
import asyncio
import logging
import httpx
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models import (
    AllocationsSnapshotRun,
    ClusterProfile,
    SnapshotRunStatus,
    SnapshotRunTrigger,
)
from app.repositories.cost_snapshot import (
    AllocationsSnapshotRunRepository,
    CostSnapshotRepository,
)
from app.services.clients import OpenCostInternalError
from app.services.factory import service_factory
from app.services.snapshot_mapping import map_pod_allocation

logger = logging.getLogger(__name__)


DEFAULT_BACKFILL_DAYS = 30
DEFAULT_INCREMENTAL_LOOKBACK_DAYS = 2  # always re-fetch last 2 days to refine
MIN_BACKFILL_DAYS = 1
MAX_BACKFILL_DAYS = 60


def _enumerate_days(window_start: datetime, window_end: datetime) -> list[date]:
    """Return the list of UTC days spanned by [window_start, window_end).

    Each emitted day is the UTC midnight that opens it. We omit the trailing
    "today-in-progress" day if window_end falls before midnight UTC of that day.
    """
    if window_end <= window_start:
        return []
    start_day = window_start.astimezone(timezone.utc).date()
    end_day = window_end.astimezone(timezone.utc).date()
    days: list[date] = []
    cursor = start_day
    while cursor <= end_day:
        days.append(cursor)
        cursor = cursor + timedelta(days=1)
    return days


def _day_window_arg(day: date) -> str:
    """OpenCost accepts ISO date pairs as the `window` parameter.

    Format: '2026-05-14T00:00:00Z,2026-05-15T00:00:00Z'.
    This is exact and avoids 'Nd' rolling-window ambiguity.
    """
    start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return f"{start.isoformat().replace('+00:00', 'Z')},{end.isoformat().replace('+00:00', 'Z')}"


class AllocationsSnapshotError(Exception):
    """Business-level snapshot error."""


class AllocationsSnapshotBusyError(AllocationsSnapshotError):
    """A RUNNING snapshot already exists for this cluster."""


class AllocationsSnapshotService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = AllocationsSnapshotRunRepository(session)

    # ── Public API ──────────────────────────────────────────────────────

    async def reserve_run(
        self,
        cluster: ClusterProfile,
        *,
        trigger: SnapshotRunTrigger,
        backfill_days: int | None = None,
    ) -> AllocationsSnapshotRun:
        """Reserve a RUNNING row.

        - trigger=SCHEDULER or MANUAL → incremental window (last N days, where N
          is computed from latest_bucket_date).
        - trigger=BACKFILL → window covers the last `backfill_days` days
          regardless of existing data; UPSERT handles overlap.
        """
        # Defensive: detect concurrent run.
        existing = await self._get_running_for_cluster(cluster.id)
        if existing is not None:
            raise AllocationsSnapshotBusyError(
                f"Cluster {cluster.id} already has a running allocations snapshot "
                f"(run_id={existing.id})"
            )

        window_start, window_end = await self._compute_window(
            cluster.id,
            trigger=trigger,
            backfill_days=backfill_days,
        )
        return await self.runs.create(
            cluster_id=cluster.id,
            trigger=trigger.value,
            window_start=window_start,
            window_end=window_end,
        )

    @staticmethod
    async def execute_run(run_id: UUID, cluster_id: UUID) -> None:
        """Run the snapshot ETL in a fresh DB session.

        Strategy: fetch one day at a time. This keeps individual OpenCost calls
        short (and within reasonable timeouts) and makes partial progress
        durable — if day 17 fails, days 1..16 are already persisted in the DB
        and a re-run will resume from where we stopped.
        """

        PER_DAY_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=10.0, pool=10.0)
        INTER_REQUEST_DELAY = 0.3  # seconds; gentle on VictoriaMetrics

        async with AsyncSessionLocal() as session:
            cluster = await session.get(ClusterProfile, cluster_id)
            if cluster is None:
                logger.error("Snapshot ETL: cluster %s vanished", cluster_id)
                return

            runs_repo = AllocationsSnapshotRunRepository(session)
            snapshots_repo = CostSnapshotRepository(session)

            run = await session.get(AllocationsSnapshotRun, run_id)
            if run is None:
                logger.error("Snapshot ETL: run %s not found", run_id)
                return

            # Build the list of day-windows we need to fetch.
            days = _enumerate_days(run.window_start, run.window_end)
            if not days:
                fresh = await session.get(AllocationsSnapshotRun, run_id)
                if fresh is not None:
                    await runs_repo.mark_success(
                        fresh, days_processed=0, rows_upserted=0
                    )
                    await session.commit()
                return

            client = await service_factory.opencost(cluster)

            total_upserted = 0
            days_processed = 0
            failed_days: list[tuple[date, str]] = []

            for idx, day in enumerate(days):
                window_arg = _day_window_arg(day)

                try:
                    allocations = await client.list_allocations(
                        window=window_arg,
                        aggregate="pod",
                        step="1d",
                        timeout=PER_DAY_TIMEOUT,
                    )
                except OpenCostInternalError as exc:
                    logger.warning(
                        "Snapshot ETL: cluster=%s day=%s OpenCost internal: %s",
                        cluster_id,
                        day,
                        exc,
                    )
                    failed_days.append((day, f"opencost: {exc}"))
                    continue
                except (httpx.HTTPError, httpx.TimeoutException) as exc:
                    logger.warning(
                        "Snapshot ETL: cluster=%s day=%s transport %s: %s",
                        cluster_id,
                        day,
                        type(exc).__name__,
                        exc,
                    )
                    failed_days.append((day, f"{type(exc).__name__}: {exc}"))
                    continue

                try:
                    rows: list[dict] = []
                    for alloc in allocations:
                        row = map_pod_allocation(alloc, cluster_id=cluster_id)
                        if row is None:
                            continue
                        # Pin bucket_date to the day we requested — defensive.
                        # OpenCost sometimes reports midnight shifts.
                        row["bucket_date"] = day
                        rows.append(row)

                    upserted = await snapshots_repo.upsert_batch(rows)
                    await session.commit()  # commit after each day for durability
                    total_upserted += upserted
                    days_processed += 1
                    logger.info(
                        "Snapshot ETL: cluster=%s day=%s rows=%d (progress %d/%d)",
                        cluster_id,
                        day,
                        upserted,
                        idx + 1,
                        len(days),
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "Snapshot ETL: cluster=%s day=%s upsert failed",
                        cluster_id,
                        day,
                    )
                    await session.rollback()
                    failed_days.append((day, f"upsert: {type(exc).__name__}: {exc}"))

                if idx + 1 < len(days):
                    await asyncio.sleep(INTER_REQUEST_DELAY)

            # Decide final run status. Partial progress counts as success if at
            # least one day was upserted; full failure is reported as failed.
            fresh = await session.get(AllocationsSnapshotRun, run_id)
            if fresh is None:
                return

            if days_processed == 0 and failed_days:
                err = "; ".join(f"{d}: {msg[:120]}" for d, msg in failed_days[:3])
                await runs_repo.mark_failed(fresh, f"all days failed: {err}")
            elif failed_days:
                # Partial success — mark success but record which days failed.
                err_summary = (
                    f"partial: {days_processed} days ok, {len(failed_days)} days failed: "
                    + "; ".join(f"{d}: {msg[:80]}" for d, msg in failed_days[:5])
                )
                fresh.status = SnapshotRunStatus.SUCCESS.value
                fresh.days_processed = days_processed
                fresh.rows_upserted = total_upserted
                fresh.error = err_summary[:2000]
                fresh.finished_at = datetime.now(timezone.utc)
                await session.flush()
            else:
                await runs_repo.mark_success(
                    fresh,
                    days_processed=days_processed,
                    rows_upserted=total_upserted,
                )
            await session.commit()

            logger.info(
                "Snapshot ETL: cluster=%s run=%s done. days_ok=%d days_failed=%d total_rows=%d",
                cluster_id,
                run_id,
                days_processed,
                len(failed_days),
                total_upserted,
            )

    # ── Internal helpers ────────────────────────────────────────────────

    async def _get_running_for_cluster(
        self, cluster_id: UUID
    ) -> AllocationsSnapshotRun | None:
        # Lightweight check; reuse the repo query pattern via a small ad-hoc query.

        stmt = (
            select(AllocationsSnapshotRun)
            .where(AllocationsSnapshotRun.cluster_id == cluster_id)
            .where(AllocationsSnapshotRun.status == SnapshotRunStatus.RUNNING.value)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _compute_window(
        self,
        cluster_id: UUID,
        *,
        trigger: SnapshotRunTrigger,
        backfill_days: int | None,
    ) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)

        if trigger == SnapshotRunTrigger.BACKFILL:
            days = backfill_days or DEFAULT_BACKFILL_DAYS
            days = max(MIN_BACKFILL_DAYS, min(days, MAX_BACKFILL_DAYS))
            return now - timedelta(days=days), now

        # Incremental: lookback is computed from the latest bucket we already have.
        snapshots_repo = CostSnapshotRepository(self.session)
        latest: date | None = await snapshots_repo.latest_bucket_date(cluster_id)

        if latest is None:
            # No data at all — treat as a small initial window. Operator should
            # use backfill explicitly for full history.
            return now - timedelta(days=DEFAULT_INCREMENTAL_LOOKBACK_DAYS), now

        # Re-fetch latest_bucket_date and a 2-day overlap to refine partial days.
        candidate_start = datetime.combine(
            latest, datetime.min.time(), tzinfo=timezone.utc
        ) - timedelta(days=DEFAULT_INCREMENTAL_LOOKBACK_DAYS)
        return candidate_start, now
