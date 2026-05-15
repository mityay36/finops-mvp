from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BillingSyncRun, SyncRunStatus


class SyncRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_cluster(
        self, cluster_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[BillingSyncRun], int]:
        total_stmt = (
            select(func.count())
            .select_from(BillingSyncRun)
            .where(BillingSyncRun.cluster_id == cluster_id)
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(BillingSyncRun)
            .where(BillingSyncRun.cluster_id == cluster_id)
            .order_by(BillingSyncRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), total

    async def get(self, run_id: UUID) -> BillingSyncRun | None:
        return await self.session.get(BillingSyncRun, run_id)

    async def get_running_for_cluster(self, cluster_id: UUID) -> BillingSyncRun | None:
        stmt = (
            select(BillingSyncRun)
            .where(BillingSyncRun.cluster_id == cluster_id)
            .where(BillingSyncRun.status == SyncRunStatus.RUNNING)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_last_success_for_cluster(self, cluster_id: UUID) -> BillingSyncRun | None:
        stmt = (
            select(BillingSyncRun)
            .where(BillingSyncRun.cluster_id == cluster_id)
            .where(BillingSyncRun.status == SyncRunStatus.SUCCESS)
            .order_by(BillingSyncRun.finished_at.desc().nullslast())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_running(
        self,
        *,
        cluster_id: UUID,
        window_start: datetime,
        window_end: datetime,
    ) -> BillingSyncRun:
        run = BillingSyncRun(
            cluster_id=cluster_id,
            status=SyncRunStatus.RUNNING,
            window_start=window_start,
            window_end=window_end,
            started_at=datetime.now(timezone.utc),
            records_imported=0,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def mark_success(
        self, run: BillingSyncRun, *, records_imported: int
    ) -> BillingSyncRun:
        run.status = SyncRunStatus.SUCCESS
        run.finished_at = datetime.now(timezone.utc)
        run.records_imported = records_imported
        run.error_message = None
        await self.session.flush()
        return run

    async def mark_failed(
        self, run: BillingSyncRun, *, error_message: str, records_imported: int = 0
    ) -> BillingSyncRun:
        run.status = SyncRunStatus.FAILED
        run.finished_at = datetime.now(timezone.utc)
        run.error_message = error_message[:2000]  # column is TEXT but be defensive in logs
        run.records_imported = records_imported
        await self.session.flush()
        return run
