"""HTTP layer for cost allocations read API.

Reads exclusively from cost_snapshots — no live OpenCost calls happen here.
Live debugging endpoint (pass-through to OpenCost) lives separately at
/allocations/live and is intended for ops, not for the dashboard.
"""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.cost_snapshot import GroupByDim
from app.schemas.allocations import (
    AllocationsAggregatedResponse,
    AllocationsTimeseriesResponse,
    AllocationsTotalsResponse,
)
from app.services.allocations_query_service import (
    AllocationsQueryService,
    InvalidPeriodError,
    resolve_period,
)
from app.services.cluster_service import ClusterNotFoundError, ClusterService

router = APIRouter()


def _cluster_service(session: AsyncSession = Depends(get_db)) -> ClusterService:
    return ClusterService(session)


def _query_service(
    session: AsyncSession = Depends(get_db),
) -> AllocationsQueryService:
    return AllocationsQueryService(session)


async def _ensure_cluster(cs: ClusterService, cluster_id: UUID) -> None:
    try:
        await cs.get_cluster(cluster_id)
    except ClusterNotFoundError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


def _resolve_period_or_422(date_from: date | None, date_to: date | None):
    try:
        return resolve_period(date_from=date_from, date_to=date_to)
    except InvalidPeriodError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@router.get(
    "/clusters/{cluster_id}/allocations/totals",
    response_model=AllocationsTotalsResponse,
)
async def get_allocations_totals(
    cluster_id: UUID,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    cs: ClusterService = Depends(_cluster_service),
    qs: AllocationsQueryService = Depends(_query_service),
) -> AllocationsTotalsResponse:
    await _ensure_cluster(cs, cluster_id)
    period = _resolve_period_or_422(date_from, date_to)
    return await qs.totals(cluster_id, period=period)


@router.get(
    "/clusters/{cluster_id}/allocations",
    response_model=AllocationsAggregatedResponse,
)
async def get_allocations_aggregated(
    cluster_id: UUID,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    group_by: GroupByDim = Query("namespace"),
    top: int | None = Query(None, ge=1, le=200),
    cs: ClusterService = Depends(_cluster_service),
    qs: AllocationsQueryService = Depends(_query_service),
) -> AllocationsAggregatedResponse:
    await _ensure_cluster(cs, cluster_id)
    period = _resolve_period_or_422(date_from, date_to)
    return await qs.aggregated(cluster_id, period=period, group_by=group_by, top=top)


@router.get(
    "/clusters/{cluster_id}/allocations/timeseries",
    response_model=AllocationsTimeseriesResponse,
)
async def get_allocations_timeseries(
    cluster_id: UUID,
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    group_by: GroupByDim | None = Query(
        None,
        description="If set, returns daily breakdown by this dimension. "
        "Otherwise returns a single cluster-wide series.",
    ),
    top: int | None = Query(
        5,
        ge=1,
        le=20,
        description="Top-N keys to include when group_by is set. Ignored otherwise.",
    ),
    cs: ClusterService = Depends(_cluster_service),
    qs: AllocationsQueryService = Depends(_query_service),
) -> AllocationsTimeseriesResponse:
    await _ensure_cluster(cs, cluster_id)
    period = _resolve_period_or_422(date_from, date_to)
    return await qs.timeseries(
        cluster_id,
        period=period,
        group_by=group_by,
        top=top if group_by else None,
    )
