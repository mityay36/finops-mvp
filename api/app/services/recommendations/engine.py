from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cluster import ClusterProfile
from app.models.recommendation import (
    RecommendationSeverity,
)
from app.models.snapshot import CostSnapshot
from app.repositories.recommendation import RecommendationRepository
from app.services.recommendations.types import (
    EvaluationContext,
    RuleEvaluator,
    RuleFinding,
)


logger = logging.getLogger(__name__)


# Severity thresholds expressed as fraction of cluster_monthly_cost.
# Per design decision (Stage 6.2): critical >= 15%, warning >= 5%.
_SEVERITY_CRITICAL = Decimal("0.15")
_SEVERITY_WARNING = Decimal("0.05")

# Constants for monthly projection / unit conversions.
_HOURS_PER_DAY = Decimal(24)
_DAYS_PER_MONTH = Decimal(30)
_GIB = Decimal(1024 * 1024 * 1024)


@dataclass
class RulePerRunReport:
    rule_id: str
    findings_count: int
    upserted: int
    auto_resolved: int
    error: str | None


@dataclass
class EngineRunReport:
    cluster_id: UUID
    valid_days: int
    cluster_monthly_cost: Decimal
    cpu_unit_cost_per_core_hour: Decimal
    ram_unit_cost_per_gib_hour: Decimal
    per_rule: dict[str, RulePerRunReport]
    skipped_reason: str | None = None

    @classmethod
    def empty(
        cls,
        cluster_id: UUID,
        *,
        reason: str,
        valid_days: int = 0,
    ) -> "EngineRunReport":
        return cls(
            cluster_id=cluster_id,
            valid_days=valid_days,
            cluster_monthly_cost=Decimal(0),
            cpu_unit_cost_per_core_hour=Decimal(0),
            ram_unit_cost_per_gib_hour=Decimal(0),
            per_rule={},
            skipped_reason=reason,
        )


class RecommendationEngineService:
    """Orchestrates rule evaluation for a single cluster on a single run.

    Workflow per cluster:
      1. Fetch the last `window_days` of snapshots (UTC days, exclusive of today).
      2. Compute aggregates needed by every rule (unit costs, cluster monthly cost).
      3. Short-circuit if valid days < min_valid_days.
      4. For each registered rule:
           a. Invoke evaluate(ctx) -> list[RuleFinding].
           b. Upsert each finding as an OPEN recommendation.
           c. Auto-resolve OPEN recommendations of this rule that did not fire.
      5. Commit once.
    """

    def __init__(
        self,
        session: AsyncSession,
        rules: Iterable[RuleEvaluator],
        *,
        window_days: int = 14,
        min_valid_days: int = 10,
    ) -> None:
        self.session = session
        self.rules: tuple[RuleEvaluator, ...] = tuple(rules)
        self.window_days = window_days
        self.min_valid_days = min_valid_days
        self.repo = RecommendationRepository(session)

    # ─── Public API ──────────────────────────────────────────────────────

    async def evaluate_cluster(self, cluster_id: UUID) -> EngineRunReport:
        """Evaluate all rules for one cluster. Returns a structured report.

        Does NOT commit — caller decides transactional boundaries.
        """
        # 1. Fetch snapshots for the window.
        today_utc = date.today()
        window_end = today_utc  # exclusive
        window_start = today_utc - timedelta(days=self.window_days)

        snapshots = await self._fetch_snapshots(cluster_id, window_start, window_end)

        if not snapshots:
            logger.info(
                "Engine: cluster %s has no snapshots in window — skipping",
                cluster_id,
            )
            return EngineRunReport.empty(cluster_id, reason="no_snapshots")

        # Distinct days actually present in the data — this is what counts as
        # "valid days" for short-circuit. A day with zero rows would not appear.
        bucket_dates = tuple(sorted({s.bucket_date for s in snapshots}))

        if len(bucket_dates) < self.min_valid_days:
            logger.info(
                "Engine: cluster %s has %d valid days (< %d required) — skipping",
                cluster_id,
                len(bucket_dates),
                self.min_valid_days,
            )
            return EngineRunReport.empty(
                cluster_id,
                reason="insufficient_days",
                valid_days=len(bucket_dates),
            )

        # 2. Compute shared aggregates.
        cluster_monthly_cost = self._project_monthly_cost(snapshots, bucket_dates)
        cpu_unit, ram_unit = self._unit_costs(snapshots)

        ctx = EvaluationContext(
            cluster_id=cluster_id,
            bucket_dates=bucket_dates,
            snapshots=tuple(snapshots),
            cluster_monthly_cost=cluster_monthly_cost,
            cpu_unit_cost_per_core_hour=cpu_unit,
            ram_unit_cost_per_gib_hour=ram_unit,
            min_valid_days=self.min_valid_days,
        )

        # 3. Run each rule.
        report = EngineRunReport(
            cluster_id=cluster_id,
            valid_days=len(bucket_dates),
            cluster_monthly_cost=cluster_monthly_cost,
            cpu_unit_cost_per_core_hour=cpu_unit,
            ram_unit_cost_per_gib_hour=ram_unit,
            per_rule={},
        )

        for rule in self.rules:
            try:
                findings = rule.evaluate(ctx)
            except Exception:
                logger.exception(
                    "Engine: rule %s crashed for cluster %s — skipping rule",
                    rule.rule_id,
                    cluster_id,
                )
                report.per_rule[rule.rule_id] = RulePerRunReport(
                    rule_id=rule.rule_id,
                    findings_count=0,
                    upserted=0,
                    auto_resolved=0,
                    error="rule_crashed",
                )
                continue

            await self._apply_findings(cluster_id, rule.rule_id, findings, ctx, report)

        return report

    # ─── Internals ───────────────────────────────────────────────────────

    async def _fetch_snapshots(
        self, cluster_id: UUID, start: date, end: date
    ) -> list[CostSnapshot]:
        stmt = (
            select(CostSnapshot)
            .where(CostSnapshot.cluster_id == cluster_id)
            .where(CostSnapshot.bucket_date >= start)
            .where(CostSnapshot.bucket_date < end)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    def _project_monthly_cost(
        snapshots: Iterable[CostSnapshot], bucket_dates: tuple[date, ...]
    ) -> Decimal:
        """Linear projection: average daily cost × 30."""
        if not bucket_dates:
            return Decimal(0)
        total = sum((s.total_cost for s in snapshots), Decimal(0))
        return (total / Decimal(len(bucket_dates))) * _DAYS_PER_MONTH

    @staticmethod
    def _unit_costs(
        snapshots: Iterable[CostSnapshot],
    ) -> tuple[Decimal, Decimal]:
        """Compute cpu $/core-hour and ram $/GiB-hour from window totals.

        Both metrics empirically stable across days (Stage 6.1 sanity:
        std/mean ≈ 5e-6), so a single window-wide ratio is more accurate
        than per-day averaging.
        """
        cpu_cost = Decimal(0)
        cpu_core_hours = Decimal(0)
        ram_cost = Decimal(0)
        ram_byte_hours = Decimal(0)
        for s in snapshots:
            cpu_cost += s.cpu_cost
            cpu_core_hours += s.cpu_core_hours
            ram_cost += s.ram_cost
            ram_byte_hours += s.ram_byte_hours

        cpu_unit = (cpu_cost / cpu_core_hours) if cpu_core_hours > 0 else Decimal(0)
        ram_byte_hour_unit = (
            (ram_cost / ram_byte_hours) if ram_byte_hours > 0 else Decimal(0)
        )
        # Convert byte-hour → GiB-hour for human-friendly numbers in evidence.
        ram_unit_per_gib = ram_byte_hour_unit * _GIB
        return cpu_unit, ram_unit_per_gib

    @classmethod
    def severity_for(
        cls, *, monthly_saving_usd: Decimal, cluster_monthly_cost: Decimal
    ) -> RecommendationSeverity:
        if cluster_monthly_cost <= 0:
            return RecommendationSeverity.INFO
        share = monthly_saving_usd / cluster_monthly_cost
        if share >= _SEVERITY_CRITICAL:
            return RecommendationSeverity.CRITICAL
        if share >= _SEVERITY_WARNING:
            return RecommendationSeverity.WARNING
        return RecommendationSeverity.INFO

    async def _apply_findings(
        self,
        cluster_id: UUID,
        rule_id: str,
        findings: list[RuleFinding],
        ctx: EvaluationContext,
        report: EngineRunReport,
    ) -> None:
        active_keys: list[tuple[str, str]] = []
        upserted = 0

        for f in findings:
            severity = self.severity_for(
                monthly_saving_usd=f.monthly_saving_usd,
                cluster_monthly_cost=ctx.cluster_monthly_cost,
            )
            await self.repo.upsert_open(
                cluster_id=cluster_id,
                rule_id=rule_id,
                target_kind=f.target_kind.value,
                target_namespace=f.target_namespace,
                target_controller=f.target_controller,
                severity=severity.value,
                monthly_saving_usd=f.monthly_saving_usd,
                evidence=f.evidence,
            )
            active_keys.append((f.target_namespace, f.target_controller))
            upserted += 1

        auto_resolved = await self.repo.auto_resolve_missing(
            cluster_id=cluster_id,
            rule_id=rule_id,
            active_keys=active_keys,
        )

        report.per_rule[rule_id] = RulePerRunReport(
            rule_id=rule_id,
            findings_count=len(findings),
            upserted=upserted,
            auto_resolved=auto_resolved,
            error=None,
        )
