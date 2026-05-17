"""Recommendation engine job — runs after the snapshot ETL completes.

Iterates active clusters sequentially; per-cluster session and commit so
one cluster's failure cannot poison others. Uses the same factory that
the on-demand refresh endpoint does — a single source of truth for
which rules are registered.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.cluster import ClusterProfile
from app.services.recommendations.factory import build_engine

logger = logging.getLogger(__name__)


async def evaluate_recommendations_for_all_active_clusters() -> None:
    """Scheduler entrypoint.

    Sequential per-cluster execution. We deliberately open a fresh session
    per cluster so that:
      - a long-running engine on cluster N doesn't hold a transaction
        across cluster N+1 (would block other writers and bloat the WAL)
      - per-cluster rollback on rule crash doesn't poison the whole batch
    """
    cluster_ids = await _list_active_cluster_ids()
    if not cluster_ids:
        logger.info("Recommendation job: no active clusters")
        return

    logger.info(
        "Recommendation job: evaluating %d clusters sequentially",
        len(cluster_ids),
    )

    succeeded = 0
    failed = 0

    for cluster_id in cluster_ids:
        try:
            await _evaluate_one(cluster_id)
            succeeded += 1
        except Exception:
            # Engine itself catches per-rule exceptions; reaching here means
            # a session-level failure (DB timeout, connection lost). We log
            # and continue — partial progress is better than total batch loss.
            logger.exception(
                "Recommendation job: cluster %s evaluation failed",
                cluster_id,
            )
            failed += 1

    logger.info(
        "Recommendation job: done — succeeded=%d failed=%d", succeeded, failed
    )


async def _list_active_cluster_ids() -> list[UUID]:
    """Read-only quick query — separate session, closed immediately."""
    async with AsyncSessionLocal() as session:
        stmt = select(ClusterProfile.id).where(ClusterProfile.is_active.is_(True))
        result = await session.execute(stmt)
        return [row[0] for row in result.all()]


async def _evaluate_one(cluster_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        engine = build_engine(session)
        report = await engine.evaluate_cluster(cluster_id)
        await session.commit()

    # Per-cluster summary log line — one message that the diss script can
    # easily grep/aggregate from production logs.
    if report.skipped_reason:
        logger.info(
            "Recommendation job: cluster=%s skipped reason=%s valid_days=%d",
            cluster_id,
            report.skipped_reason,
            report.valid_days,
        )
        return

    total_findings = sum(r.findings_count for r in report.per_rule.values())
    total_resolved = sum(r.auto_resolved for r in report.per_rule.values())
    logger.info(
        "Recommendation job: cluster=%s rules=%d findings=%d auto_resolved=%d "
        "monthly_cost=$%.2f",
        cluster_id,
        len(report.per_rule),
        total_findings,
        total_resolved,
        report.cluster_monthly_cost,
    )
