"""Thin service wrapping repository + schema mapping.

Kept separate from RecommendationEngineService — engine is a write-path
batch worker, this is the read/lifecycle path triggered by HTTP.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import Recommendation
from app.repositories.recommendation import RecommendationRepository
from app.schemas.recommendation import (
    PaginationMeta,
    RecommendationDetail,
    RecommendationItem,
    RecommendationListResponse,
    impact_kind_for,
)


class RecommendationApiService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RecommendationRepository(session)

    async def list(
        self,
        cluster_id: UUID,
        *,
        limit: int,
        offset: int,
        statuses: list[str] | None,
        severities: list[str] | None,
        rule_ids: list[str] | None,
        namespaces: list[str] | None,
        min_saving_usd: Decimal | None,
    ) -> RecommendationListResponse:
        # Run count and rows in parallel? Not worth it on this scale —
        # both are sub-millisecond on typical filter sets.
        total = await self.repo.count_for_cluster(
            cluster_id,
            statuses=statuses,
            severities=severities,
            rule_ids=rule_ids,
            namespaces=namespaces,
            min_saving_usd=min_saving_usd,
        )
        rows = await self.repo.list_for_cluster(
            cluster_id,
            limit=limit,
            offset=offset,
            statuses=statuses,
            severities=severities,
            rule_ids=rule_ids,
            namespaces=namespaces,
            min_saving_usd=min_saving_usd,
        )
        return RecommendationListResponse(
            items=[_to_item(r) for r in rows],
            pagination=PaginationMeta(
                total=total,
                limit=limit,
                offset=offset,
                has_more=(offset + len(rows)) < total,
            ),
        )

    async def get(self, cluster_id: UUID, rec_id: UUID) -> RecommendationDetail | None:
        row = await self.repo.get_by_id(cluster_id, rec_id)
        if row is None:
            return None
        return _to_detail(row)

    async def apply(
        self, cluster_id: UUID, rec_id: UUID
    ) -> RecommendationDetail | None:
        row = await self.repo.transition_status(
            cluster_id,
            rec_id,
            from_status="open",
            to_status="applied",
            dismissed_reason=None,
        )
        if row is None:
            return None
        return _to_detail(row)

    async def dismiss(
        self, cluster_id: UUID, rec_id: UUID, *, reason: str
    ) -> RecommendationDetail | None:
        row = await self.repo.transition_status(
            cluster_id,
            rec_id,
            from_status="open",
            to_status="dismissed",
            dismissed_reason=reason,
        )
        if row is None:
            return None
        return _to_detail(row)


# ─── Mappers ─────────────────────────────────────────────────────────────


def _to_item(r: Recommendation) -> RecommendationItem:
    return RecommendationItem(
        id=r.id,
        cluster_id=r.cluster_id,
        rule_id=r.rule_id,
        target_kind=r.target_kind,
        target_namespace=r.target_namespace,
        target_controller=r.target_controller,
        status=r.status,  # type: ignore[arg-type]
        severity=r.severity,  # type: ignore[arg-type]
        monthly_impact_usd=r.monthly_saving_usd,
        impact_kind=impact_kind_for(r.rule_id),
        first_seen_at=r.first_seen_at,
        last_seen_at=r.last_seen_at,
        resolved_at=r.resolved_at,
        dismissed_reason=r.dismissed_reason,
    )


def _to_detail(r: Recommendation) -> RecommendationDetail:
    return RecommendationDetail(
        id=r.id,
        cluster_id=r.cluster_id,
        rule_id=r.rule_id,
        target_kind=r.target_kind,
        target_namespace=r.target_namespace,
        target_controller=r.target_controller,
        status=r.status,  # type: ignore[arg-type]
        severity=r.severity,  # type: ignore[arg-type]
        monthly_impact_usd=r.monthly_saving_usd,
        impact_kind=impact_kind_for(r.rule_id),
        first_seen_at=r.first_seen_at,
        last_seen_at=r.last_seen_at,
        resolved_at=r.resolved_at,
        dismissed_reason=r.dismissed_reason,
        evidence=r.evidence,
    )
