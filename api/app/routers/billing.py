from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.sync_run import SyncRunRepository
from app.schemas import (
    BillingSummary,
    BillingTimeseries,
    BillingTopResources,
)
from app.services.billing_service import (
    BillingService,
    BillingValidationError,
    MultipleCurrenciesError,
)
from app.services.cluster_service import ClusterNotFoundError, ClusterService

router = APIRouter()


def _cluster_service(session: AsyncSession = Depends(get_db)) -> ClusterService:
    return ClusterService(session)


def _billing_service(session: AsyncSession = Depends(get_db)) -> BillingService:
    return BillingService(session)


def _runs_repo(session: AsyncSession = Depends(get_db)) -> SyncRunRepository:
    return SyncRunRepository(session)


async def _ensure_cluster(cluster_service: ClusterService, cluster_id: UUID) -> None:
    try:
        await cluster_service.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _handle_billing_errors(exc: BillingValidationError) -> HTTPException:
    if isinstance(exc, MultipleCurrenciesError):
        return HTTPException(status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get(
    "/clusters/{cluster_id}/billing/summary",
    response_model=BillingSummary,
)
async def get_billing_summary(
    cluster_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    cluster_service: ClusterService = Depends(_cluster_service),
    billing_service: BillingService = Depends(_billing_service),
) -> BillingSummary:
    await _ensure_cluster(cluster_service, cluster_id)
    try:
        return await billing_service.get_summary(cluster_id, period_start, period_end)
    except BillingValidationError as exc:
        raise _handle_billing_errors(exc) from exc


@router.get(
    "/clusters/{cluster_id}/billing/timeseries",
    response_model=BillingTimeseries,
)
async def get_billing_timeseries(
    cluster_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    granularity: str = Query("daily", pattern="^(daily|weekly)$"),
    group_by: str = Query("total", pattern="^(total|service)$"),
    cluster_service: ClusterService = Depends(_cluster_service),
    billing_service: BillingService = Depends(_billing_service),
) -> BillingTimeseries:
    await _ensure_cluster(cluster_service, cluster_id)
    try:
        return await billing_service.get_timeseries(
            cluster_id, period_start, period_end, granularity, group_by
        )
    except BillingValidationError as exc:
        raise _handle_billing_errors(exc) from exc


@router.get(
    "/clusters/{cluster_id}/billing/top-resources",
    response_model=BillingTopResources,
)
async def get_billing_top_resources(
    cluster_id: UUID,
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
    limit: int = Query(20, ge=1, le=200),
    cluster_service: ClusterService = Depends(_cluster_service),
    billing_service: BillingService = Depends(_billing_service),
) -> BillingTopResources:
    await _ensure_cluster(cluster_service, cluster_id)
    try:
        return await billing_service.get_top_resources(
            cluster_id, period_start, period_end, limit
        )
    except BillingValidationError as exc:
        raise _handle_billing_errors(exc) from exc
