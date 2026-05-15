import logging
import traceback
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.credentials import resolve_credentials
from app.core.database import AsyncSessionLocal
from app.models import BillingSyncRun, ClusterProfile, ProviderType
from app.providers import get_provider
from app.providers.dto import BillingRecordDTO
from app.repositories.billing import BillingRepository
from app.repositories.sync_run import SyncRunRepository

logger = logging.getLogger(__name__)


DEFAULT_OVERLAP_DAYS = 3
DEFAULT_MAX_LOOKBACK_DAYS = 35
INSERT_BATCH_SIZE = 500


class BillingSyncError(Exception):
    """Raised on business-level sync failures."""


class BillingSyncBusyError(BillingSyncError):
    """Raised when there is already a RUNNING sync for the cluster."""


class BillingSyncService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.runs = SyncRunRepository(session)

    # ── Public API used by routers ───────────────────────────────────────

    async def reserve_run(
        self,
        cluster: ClusterProfile,
        *,
        force_full: bool = False,
    ) -> BillingSyncRun:
        """Atomically check for concurrent run and create a RUNNING row.

        Caller is expected to commit immediately after this returns so the row
        is visible to other transactions. The actual ETL work happens in a
        separate session via execute_run().
        """
        if cluster.provider_type != ProviderType.YC:
            raise BillingSyncError(
                f"Provider {cluster.provider_type.value} does not support billing sync"
            )

        existing = await self.runs.get_running_for_cluster(cluster.id)
        if existing is not None:
            raise BillingSyncBusyError(
                f"Cluster {cluster.id} already has a running sync (run_id={existing.id})"
            )

        window_start, window_end = await self._compute_window(cluster.id, force_full=force_full)
        return await self.runs.create_running(
            cluster_id=cluster.id,
            window_start=window_start,
            window_end=window_end,
        )

    @staticmethod
    async def execute_run(run_id: UUID, cluster_id: UUID) -> None:
        """Run the ETL in a fresh DB session. Designed to be invoked from a
        BackgroundTask or APScheduler job — never from a request-bound session.
        """
        async with AsyncSessionLocal() as session:
            cluster = await session.get(ClusterProfile, cluster_id)
            if cluster is None:
                logger.error("ETL: cluster %s vanished before execution", cluster_id)
                return

            runs_repo = SyncRunRepository(session)
            run = await runs_repo.get(run_id)
            if run is None:
                logger.error("ETL: run %s not found", run_id)
                return

            try:
                creds = await resolve_credentials(session, cluster_id)
            except Exception as exc:  # noqa: BLE001
                logger.exception("ETL: failed to resolve credentials")
                await runs_repo.mark_failed(run, error_message=f"credentials: {exc}")
                await session.commit()
                return

            provider_cls = get_provider(cluster.provider_type)
            provider = provider_cls()

            billing_repo = BillingRepository(session)
            inserted_total = 0
            buffer: list[BillingRecordDTO] = []

            try:
                async for dto in provider.iter_billing_records(
                    creds,
                    since=run.window_start,
                    until=run.window_end,
                ):
                    buffer.append(dto)
                    if len(buffer) >= INSERT_BATCH_SIZE:
                        inserted_total += await billing_repo.insert_batch(cluster_id, buffer)
                        buffer.clear()
                        await session.commit()  # commit per batch — observability + memory

                if buffer:
                    inserted_total += await billing_repo.insert_batch(cluster_id, buffer)
                    buffer.clear()

                # Refresh the run object (its session attributes may have detached after commits).
                run = await runs_repo.get(run_id)
                if run is not None:
                    await runs_repo.mark_success(run, records_imported=inserted_total)
                await session.commit()
                logger.info(
                    "ETL: cluster=%s run=%s inserted=%d",
                    cluster_id,
                    run_id,
                    inserted_total,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("ETL: cluster=%s run=%s failed", cluster_id, run_id)
                await session.rollback()
                # Re-fetch run inside a clean transaction to mark it failed.
                fresh = await runs_repo.get(run_id)
                if fresh is not None:
                    await runs_repo.mark_failed(
                        fresh,
                        error_message=f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}",
                        records_imported=inserted_total,
                    )
                    await session.commit()

    # ── Window computation (hybrid strategy) ─────────────────────────────

    async def _compute_window(
        self, cluster_id: UUID, *, force_full: bool
    ) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        max_lookback_start = now - timedelta(days=DEFAULT_MAX_LOOKBACK_DAYS)

        if force_full:
            return max_lookback_start, now

        last = await self.runs.get_last_success_for_cluster(cluster_id)
        if last is None:
            return max_lookback_start, now

        candidate_start = last.window_end - timedelta(days=DEFAULT_OVERLAP_DAYS)
        if candidate_start < max_lookback_start:
            candidate_start = max_lookback_start
        return candidate_start, now
