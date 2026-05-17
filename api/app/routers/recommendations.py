"""Recommendations API.

  GET    /clusters/{cluster_id}/recommendations
  GET    /clusters/{cluster_id}/recommendations/{rec_id}
  POST   /clusters/{cluster_id}/recommendations/{rec_id}/apply
  POST   /clusters/{cluster_id}/recommendations/{rec_id}/dismiss

Filters on list (all optional):
  status     — repeatable: open|applied|dismissed|closed_resolved
  severity   — repeatable: info|warning|critical
  rule_id    — repeatable
  namespace  — repeatable
  min_saving_usd
  limit (default 50, max 200), offset (default 0)
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db  # подкорректируй под свой реальный путь
from app.schemas.recommendation import (
    DismissRequest,
    RecommendationDetail,
    RecommendationListResponse,
    RecommendationRefreshResponse,
)
from app.models import ClusterProfile
from app.services.recommendations.api_service import RecommendationApiService

router = APIRouter(
    prefix="/clusters/{cluster_id}/recommendations", tags=["recommendations"]
)


_LIMIT_DEFAULT = 50
_LIMIT_MAX = 200


@router.get("", response_model=RecommendationListResponse)
async def list_recommendations(
    cluster_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(_LIMIT_DEFAULT, ge=1, le=_LIMIT_MAX),
    offset: int = Query(0, ge=0),
    status_: list[str] | None = Query(default=None, alias="status"),
    severity: list[str] | None = Query(default=None),
    rule_id: list[str] | None = Query(default=None),
    namespace: list[str] | None = Query(default=None),
    min_saving_usd: Decimal | None = Query(default=None, ge=0),
) -> RecommendationListResponse:
    svc = RecommendationApiService(session)
    return await svc.list(
        cluster_id,
        limit=limit,
        offset=offset,
        statuses=status_,
        severities=severity,
        rule_ids=rule_id,
        namespaces=namespace,
        min_saving_usd=min_saving_usd,
    )


@router.get("/{rec_id}", response_model=RecommendationDetail)
async def get_recommendation(
    cluster_id: UUID,
    rec_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationDetail:
    svc = RecommendationApiService(session)
    detail = await svc.get(cluster_id, rec_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    return detail


@router.post(
    "/{rec_id}/apply",
    response_model=RecommendationDetail,
    status_code=status.HTTP_200_OK,
)
async def apply_recommendation(
    cluster_id: UUID,
    rec_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationDetail:
    svc = RecommendationApiService(session)
    # We need to distinguish 404 (no row at all) from 409 (row exists but
    # status != open). Cheap second lookup if transition fails.
    detail = await svc.apply(cluster_id, rec_id)
    if detail is not None:
        await session.commit()
        return detail

    existing = await svc.get(cluster_id, rec_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    raise HTTPException(
        status_code=409,
        detail=f"cannot apply: current status is '{existing.status}'",
    )


@router.post(
    "/{rec_id}/dismiss",
    response_model=RecommendationDetail,
    status_code=status.HTTP_200_OK,
)
async def dismiss_recommendation(
    cluster_id: UUID,
    rec_id: UUID,
    body: DismissRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationDetail:
    svc = RecommendationApiService(session)
    detail = await svc.dismiss(cluster_id, rec_id, reason=body.reason)
    if detail is not None:
        await session.commit()
        return detail

    existing = await svc.get(cluster_id, rec_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="recommendation not found")
    raise HTTPException(
        status_code=409,
        detail=f"cannot dismiss: current status is '{existing.status}'",
    )


@router.post(
    "/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RecommendationRefreshResponse,
)
async def refresh_recommendations(
    cluster_id: UUID,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RecommendationRefreshResponse:
    """Trigger an on-demand engine run for one cluster.

    Returns 202 immediately; the engine runs in a background task with
    its own session. The client should re-query the list endpoint to
    see updated recommendations.

    Why background: a typical run on a 14-day window with 3 rules takes
    ~200ms today, but with more rules / longer windows / busier clusters
    this could grow. Returning 202 lets the UI stay responsive and is
    the same pattern most ops/admin actions use.
    """
    # Cheap existence check — fail fast if cluster doesn't exist or is inactive.
    cluster = await _get_active_cluster(session, cluster_id)
    if cluster is None:
        raise HTTPException(
            status_code=404,
            detail="cluster not found or inactive",
        )

    background_tasks.add_task(_evaluate_one_for_endpoint, cluster_id)
    return RecommendationRefreshResponse(
        cluster_id=cluster_id,
        accepted=True,
        message="Engine run scheduled. Re-query list to see updates.",
    )


async def _get_active_cluster(
    session: AsyncSession, cluster_id: UUID
) -> ClusterProfile | None:
    stmt = (
        select(ClusterProfile)
        .where(ClusterProfile.id == cluster_id)
        .where(ClusterProfile.is_active.is_(True))
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _evaluate_one_for_endpoint(cluster_id: UUID) -> None:
    """Background task — needs its own session, see job's _evaluate_one."""
    from app.jobs.recommendations import _evaluate_one

    await _evaluate_one(cluster_id)
