from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Iterable
from uuid import UUID

from sqlalchemy import and_, select, update, text, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation import (
    Recommendation,
    RecommendationStatus,
)


# A natural-key tuple used by the engine to express "these are the keys
# the rule fired on this evaluation". Anything OPEN with the same
# (cluster_id, rule_id) NOT in this set will be auto-resolved.
NaturalKey = tuple[str, str, str]  # (rule_id, target_namespace, target_controller)


class RecommendationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Engine-side: upsert active recommendation ───────────────────────
    async def upsert_open(
        self,
        *,
        cluster_id: UUID,
        rule_id: str,
        target_kind: str,
        target_namespace: str,
        target_controller: str,
        severity: str,
        monthly_saving_usd: Decimal,
        evidence: dict[str, Any],
    ) -> Recommendation:
        """Create or refresh an OPEN recommendation.

        Idempotent against (cluster_id, rule_id, ns, controller) WHERE status='open'.
        Does NOT touch closed rows of the same key.
        """
        now = datetime.now(timezone.utc)

        insert_stmt = pg_insert(Recommendation).values(
            cluster_id=cluster_id,
            rule_id=rule_id,
            target_kind=target_kind,
            target_namespace=target_namespace,
            target_controller=target_controller,
            status=RecommendationStatus.OPEN.value,
            severity=severity,
            monthly_saving_usd=monthly_saving_usd,
            evidence=evidence,
            first_seen_at=now,
            last_seen_at=now,
        )

        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[
                "cluster_id",
                "rule_id",
                "target_namespace",
                "target_controller",
            ],
            index_where=text("status = 'open'"),
            set_={
                "severity": insert_stmt.excluded.severity,
                "monthly_saving_usd": insert_stmt.excluded.monthly_saving_usd,
                "evidence": insert_stmt.excluded.evidence,
                "last_seen_at": now,
            },
        ).returning(Recommendation)

        result = await self.session.execute(stmt)
        obj = result.scalars().first()
        if obj is None:
            raise RuntimeError(
                f"upsert_open returned no row for cluster={cluster_id} rule={rule_id} "
                f"ns={target_namespace} ctrl={target_controller}"
            )
        return obj

    # ── Engine-side: close everything OPEN that did NOT fire this run ───
    async def auto_resolve_missing(
        self,
        *,
        cluster_id: UUID,
        rule_id: str,
        active_keys: Iterable[tuple[str, str]],
    ) -> int:
        """Mark all OPEN rows of `rule_id` not in `active_keys` as closed_resolved.

        active_keys = iterable of (target_namespace, target_controller).
        Returns number of rows transitioned.
        """
        active = list({(ns, ctrl) for ns, ctrl in active_keys})
        now = datetime.now(timezone.utc)

        # Build a NOT IN ... compatible expression. For an empty set,
        # we want to close ALL open rows of this rule.
        base_filter = and_(
            Recommendation.cluster_id == cluster_id,
            Recommendation.rule_id == rule_id,
            Recommendation.status == RecommendationStatus.OPEN.value,
        )

        if active:
            # Use tuple_() for composite NOT IN, but PostgreSQL handles this
            # natively via row constructor.
            from sqlalchemy import tuple_

            base_filter = and_(
                base_filter,
                tuple_(
                    Recommendation.target_namespace,
                    Recommendation.target_controller,
                ).notin_(active),
            )

        stmt = (
            update(Recommendation)
            .where(base_filter)
            .values(
                status=RecommendationStatus.CLOSED_RESOLVED.value,
                resolved_at=now,
            )
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    # ── User-side actions ───────────────────────────────────────────────
    async def mark_applied(self, rec_id: UUID) -> Recommendation | None:
        return await self._transition(
            rec_id,
            new_status=RecommendationStatus.APPLIED,
            require_status=RecommendationStatus.OPEN,
        )

    async def mark_dismissed(
        self, rec_id: UUID, *, reason: str
    ) -> Recommendation | None:
        return await self._transition(
            rec_id,
            new_status=RecommendationStatus.DISMISSED,
            require_status=RecommendationStatus.OPEN,
            extra={"dismissed_reason": reason},
        )

    async def _transition(
        self,
        rec_id: UUID,
        *,
        new_status: RecommendationStatus,
        require_status: RecommendationStatus,
        extra: dict[str, Any] | None = None,
    ) -> Recommendation | None:
        now = datetime.now(timezone.utc)
        values: dict[str, Any] = {
            "status": new_status.value,
            "resolved_at": now,
        }
        if extra:
            values.update(extra)

        stmt = (
            update(Recommendation)
            .where(
                and_(
                    Recommendation.id == rec_id,
                    Recommendation.status == require_status.value,
                )
            )
            .values(**values)
            .returning(Recommendation.id)
        )
        result = await self.session.execute(stmt)
        if result.first() is None:
            return None
        return await self.session.get(Recommendation, rec_id)

    # ── Read-API ────────────────────────────────────────────────────────
    async def list_for_cluster(
        self,
        cluster_id: UUID,
        *,
        limit: int,
        offset: int,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
        rule_ids: list[str] | None = None,
        namespaces: list[str] | None = None,
        min_saving_usd: Decimal | None = None,
    ) -> list[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.cluster_id == cluster_id)
        stmt = self._apply_filters(
            stmt,
            statuses=statuses,
            severities=severities,
            rule_ids=rule_ids,
            namespaces=namespaces,
            min_saving_usd=min_saving_usd,
        )
        # Stable ordering: $-impact desc, then id for determinism on ties.
        stmt = (
            stmt.order_by(
                Recommendation.monthly_saving_usd.desc(),
                Recommendation.id.asc(),
            )
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_cluster(
        self,
        cluster_id: UUID,
        *,
        statuses: list[str] | None = None,
        severities: list[str] | None = None,
        rule_ids: list[str] | None = None,
        namespaces: list[str] | None = None,
        min_saving_usd: Decimal | None = None,
    ) -> int:
        stmt = select(func.count(Recommendation.id)).where(
            Recommendation.cluster_id == cluster_id
        )
        stmt = self._apply_filters(
            stmt,
            statuses=statuses,
            severities=severities,
            rule_ids=rule_ids,
            namespaces=namespaces,
            min_saving_usd=min_saving_usd,
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, cluster_id: UUID, rec_id: UUID) -> Recommendation | None:
        stmt = (
            select(Recommendation)
            .where(Recommendation.cluster_id == cluster_id)
            .where(Recommendation.id == rec_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    def _apply_filters(
        stmt, *, statuses, severities, rule_ids, namespaces, min_saving_usd
    ):
        if statuses:
            stmt = stmt.where(Recommendation.status.in_(statuses))
        if severities:
            stmt = stmt.where(Recommendation.severity.in_(severities))
        if rule_ids:
            stmt = stmt.where(Recommendation.rule_id.in_(rule_ids))
        if namespaces:
            stmt = stmt.where(Recommendation.target_namespace.in_(namespaces))
        if min_saving_usd is not None:
            stmt = stmt.where(Recommendation.monthly_saving_usd >= min_saving_usd)
        return stmt

    # ─── Lifecycle transitions ───────────────────────────────────────────

    async def transition_status(
        self,
        cluster_id: UUID,
        rec_id: UUID,
        *,
        from_status: str,
        to_status: str,
        dismissed_reason: str | None = None,
    ) -> Recommendation | None:
        """Atomic conditional update.

        Returns the updated row, or None if the precondition (current
        status == from_status) didn't hold. The caller maps None → 409.
        We use UPDATE ... RETURNING in a single statement so that two
        concurrent apply/dismiss requests can't both succeed.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        stmt = (
            update(Recommendation)
            .where(Recommendation.cluster_id == cluster_id)
            .where(Recommendation.id == rec_id)
            .where(Recommendation.status == from_status)
            .values(
                status=to_status,
                resolved_at=now,
                dismissed_reason=dismissed_reason,
            )
            .returning(Recommendation)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row
