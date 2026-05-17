from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.sync_run import SyncRunRepository
from app.schemas import BillingSyncRunRead, Page, LatestSyncRun
from app.models import SyncRunStatus
from app.services.billing_sync_service import (
    BillingSyncBusyError,
    BillingSyncError,
    BillingSyncService,
)
from app.services.cluster_service import ClusterNotFoundError, ClusterService

from app.models import SnapshotRunTrigger
from app.repositories.cost_snapshot import AllocationsSnapshotRunRepository
from app.schemas import AllocationsSnapshotRunRead, LatestAllocationsSnapshotRun
from app.services.allocations_snapshot_service import (
    AllocationsSnapshotBusyError,
    AllocationsSnapshotError,
    AllocationsSnapshotService,
)


router = APIRouter()


def _cluster_service(session: AsyncSession = Depends(get_db)) -> ClusterService:
    return ClusterService(session)


def _sync_service(session: AsyncSession = Depends(get_db)) -> BillingSyncService:
    return BillingSyncService(session)


def _runs_repo(session: AsyncSession = Depends(get_db)) -> SyncRunRepository:
    return SyncRunRepository(session)


@router.post(
    "/clusters/{cluster_id}/sync/billing",
    response_model=BillingSyncRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_billing_sync(
    cluster_id: UUID,
    background_tasks: BackgroundTasks,
    force_full: bool = Query(
        False, description="Ignore incremental window, fetch full lookback."
    ),
    cluster_service: ClusterService = Depends(_cluster_service),
    sync_service: BillingSyncService = Depends(_sync_service),
) -> BillingSyncRunRead:
    """Trigger a billing sync for the cluster. The HTTP response returns immediately
    with the reserved run record (status=running). Actual ETL work happens in a
    BackgroundTask in a separate DB session."""
    try:
        cluster = await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    try:
        run = await sync_service.reserve_run(cluster, force_full=force_full)
        await sync_service.session.commit()
    except BillingSyncBusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except BillingSyncError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    background_tasks.add_task(BillingSyncService.execute_run, run.id, cluster_id)
    return BillingSyncRunRead.model_validate(run)


@router.get(
    "/clusters/{cluster_id}/sync/billing/runs",
    response_model=Page[BillingSyncRunRead],
)
async def list_billing_sync_runs(
    cluster_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cluster_service: ClusterService = Depends(_cluster_service),
    runs_repo: SyncRunRepository = Depends(_runs_repo),
) -> Page[BillingSyncRunRead]:
    try:
        await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    items, total = await runs_repo.list_for_cluster(
        cluster_id, limit=limit, offset=offset
    )
    return Page[BillingSyncRunRead](
        items=[BillingSyncRunRead.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/clusters/{cluster_id}/sync/billing/runs/latest",
    response_model=LatestSyncRun,
)
async def get_latest_billing_sync_run(
    cluster_id: UUID,
    cluster_service: ClusterService = Depends(_cluster_service),
    runs_repo: SyncRunRepository = Depends(_runs_repo),
) -> LatestSyncRun:
    try:
        await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    run = await runs_repo.get_last_success_for_cluster(cluster_id)
    if run is None or run.status != SyncRunStatus.SUCCESS or run.finished_at is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No successful billing sync runs for this cluster yet",
        )
    return LatestSyncRun.model_validate(run)


@router.get(
    "/clusters/{cluster_id}/sync/billing/runs/{run_id}",
    response_model=BillingSyncRunRead,
)
async def get_billing_sync_run(
    cluster_id: UUID,
    run_id: UUID,
    cluster_service: ClusterService = Depends(_cluster_service),
    runs_repo: SyncRunRepository = Depends(_runs_repo),
) -> BillingSyncRunRead:
    try:
        await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    run = await runs_repo.get(run_id)
    if run is None or run.cluster_id != cluster_id:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Sync run {run_id} not found"
        )
    return BillingSyncRunRead.model_validate(run)


def _alloc_snapshot_service(
    session: AsyncSession = Depends(get_db),
) -> AllocationsSnapshotService:
    return AllocationsSnapshotService(session)


def _alloc_runs_repo(
    session: AsyncSession = Depends(get_db),
) -> AllocationsSnapshotRunRepository:
    return AllocationsSnapshotRunRepository(session)


@router.post(
    "/clusters/{cluster_id}/sync/allocations",
    response_model=AllocationsSnapshotRunRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_allocations_snapshot(
    cluster_id: UUID,
    background_tasks: BackgroundTasks,
    backfill_days: int | None = Query(
        None,
        ge=1,
        le=60,
        description="If set, run a backfill snapshot covering the last N days. "
        "Otherwise an incremental snapshot is performed.",
    ),
    cluster_service: ClusterService = Depends(_cluster_service),
    snap_service: AllocationsSnapshotService = Depends(_alloc_snapshot_service),
) -> AllocationsSnapshotRunRead:
    try:
        cluster = await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    trigger = (
        SnapshotRunTrigger.BACKFILL if backfill_days else SnapshotRunTrigger.MANUAL
    )

    try:
        run = await snap_service.reserve_run(
            cluster, trigger=trigger, backfill_days=backfill_days
        )
        await snap_service.session.commit()
    except AllocationsSnapshotBusyError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except AllocationsSnapshotError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    background_tasks.add_task(
        AllocationsSnapshotService.execute_run, run.id, cluster_id
    )
    return AllocationsSnapshotRunRead.model_validate(run)


@router.get(
    "/clusters/{cluster_id}/sync/allocations/runs",
    response_model=Page[AllocationsSnapshotRunRead],
)
async def list_allocations_snapshot_runs(
    cluster_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    cluster_service: ClusterService = Depends(_cluster_service),
    runs_repo: AllocationsSnapshotRunRepository = Depends(_alloc_runs_repo),
) -> Page[AllocationsSnapshotRunRead]:
    try:
        await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    items, total = await runs_repo.list_for_cluster(
        cluster_id, limit=limit, offset=offset
    )
    return Page[AllocationsSnapshotRunRead](
        items=[AllocationsSnapshotRunRead.model_validate(r) for r in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/clusters/{cluster_id}/sync/allocations/runs/latest",
    response_model=LatestAllocationsSnapshotRun,
)
async def get_latest_allocations_snapshot_run(
    cluster_id: UUID,
    cluster_service: ClusterService = Depends(_cluster_service),
    runs_repo: AllocationsSnapshotRunRepository = Depends(_alloc_runs_repo),
) -> LatestAllocationsSnapshotRun:
    try:
        await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    run = await runs_repo.get_last_for_cluster(cluster_id)
    if run is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="No allocations snapshot runs for this cluster yet",
        )
    return LatestAllocationsSnapshotRun.model_validate(run)
