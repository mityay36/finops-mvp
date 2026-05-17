"""Rightsizing CPU rule.

Detects controllers whose CPU requests substantially exceed actual usage
over the evaluation window. Computes monthly saving from the delta between
median(requested) and p95(used) × (1 + safety_margin), priced at the
cluster's empirical $/core-hour.

Design references (Stage 6.4 decisions):
  - Aggregate at controller level (not pod): users edit Deployment specs,
    not individual pods.
  - p95 of usage protects against transient spikes shaping the recommendation.
  - median of requested tolerates mid-window edits to controller manifests.
  - safety_margin = 0.3 follows common capacity-planning practice (room
    for noisy neighbors, periodic batch jobs, GC pressure).
  - DaemonSets are included with a hint in evidence — operators must
    consider per-node cost amplification before applying.
  - Unallocated rows are skipped (pure aggregation artifact).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from statistics import median

from app.models.recommendation import RecommendationTargetKind, RuleId
from app.models.snapshot import UNALLOCATED, CostSnapshot
from app.services.recommendations.types import (
    EvaluationContext,
    RuleFinding,
)


# Tunable thresholds — kept module-level constants for now; promote to
# config if/when we expose per-cluster overrides.
_SAFETY_MARGIN = Decimal("0.3")
_MIN_MONTHLY_SAVING_USD = Decimal("5.00")
_MIN_DAYS_WITH_REQUEST = 10
_MONTHLY_HOURS = Decimal(720)  # 24 × 30
_P95_INDEX_FRACTION = Decimal("0.95")


class RightsizingCpuRule:
    rule_id: str = RuleId.RIGHTSIZING_CPU.value

    def evaluate(self, ctx: EvaluationContext) -> list[RuleFinding]:
        # 1. Aggregate per-day, per-controller: sum across pods of the same controller.
        # Key: (namespace, controller, controller_kind), value: per-day sums.
        by_target: dict[
            tuple[str, str, str],
            dict[date, _DayAccumulator],
        ] = defaultdict(lambda: defaultdict(_DayAccumulator))

        for s in ctx.snapshots:
            if s.controller == UNALLOCATED:
                continue
            key = (s.namespace, s.controller, s.controller_kind)
            acc = by_target[key][s.bucket_date]
            acc.add(s)

        findings: list[RuleFinding] = []

        for (namespace, controller, controller_kind), per_day in by_target.items():
            finding = self._evaluate_target(
                namespace=namespace,
                controller=controller,
                controller_kind=controller_kind,
                per_day=per_day,
                ctx=ctx,
            )
            if finding is not None:
                findings.append(finding)

        return findings

    def _evaluate_target(
        self,
        *,
        namespace: str,
        controller: str,
        controller_kind: str,
        per_day: dict[date, "_DayAccumulator"],
        ctx: EvaluationContext,
    ) -> RuleFinding | None:
        # Days with valid request data — required floor for the rule to fire.
        valid_days = [d for d, acc in per_day.items() if acc.cores_requested > 0]
        if len(valid_days) < _MIN_DAYS_WITH_REQUEST:
            return None

        requested_series = [per_day[d].cores_requested for d in valid_days]
        used_series = [per_day[d].cores_used for d in valid_days]
        pods_series = [per_day[d].pods for d in valid_days]

        cores_requested_median = median(requested_series)
        cores_used_p95 = _percentile(used_series, _P95_INDEX_FRACTION)

        cores_recommended = cores_used_p95 * (Decimal(1) + _SAFETY_MARGIN)
        cores_delta = cores_requested_median - cores_recommended

        if cores_delta <= 0:
            return None

        monthly_saving = cores_delta * ctx.cpu_unit_cost_per_core_hour * _MONTHLY_HOURS

        if monthly_saving < _MIN_MONTHLY_SAVING_USD:
            return None

        evidence = {
            "rule_version": "1.0",
            "days_evaluated": len(valid_days),
            "cores_requested_median": _q(cores_requested_median, 6),
            "cores_used_p95": _q(cores_used_p95, 6),
            "cores_recommended": _q(cores_recommended, 6),
            "cores_delta": _q(cores_delta, 6),
            "safety_margin": str(_SAFETY_MARGIN),
            "cpu_unit_cost_per_core_hour": _q(ctx.cpu_unit_cost_per_core_hour, 8),
            "monthly_hours": int(_MONTHLY_HOURS),
            "controller_kind": controller_kind,
            "pods_per_day_avg": _q(
                sum(pods_series, Decimal(0)) / Decimal(len(pods_series)), 2
            ),
            "monthly_saving_usd": _q(monthly_saving, 4),
        }

        return RuleFinding(
            target_kind=RecommendationTargetKind.CONTROLLER,
            target_namespace=namespace,
            target_controller=controller,
            monthly_saving_usd=_q_decimal(monthly_saving, 4),
            evidence=evidence,
        )


# ─── Helpers ─────────────────────────────────────────────────────────────


class _DayAccumulator:
    """Sums CPU request/usage across all pods of a controller on a given day.

    `pods` is the count of pod-level rows that contributed — used for
    operator context in evidence (helps explain "why is requested 0.6 — is
    that 6 pods × 0.1 or 1 pod × 0.6?").
    """

    __slots__ = ("cores_requested", "cores_used", "pods")

    def __init__(self) -> None:
        self.cores_requested: Decimal = Decimal(0)
        self.cores_used: Decimal = Decimal(0)
        self.pods: int = 0

    def add(self, s: CostSnapshot) -> None:
        self.cores_requested += s.cpu_cores_requested
        self.cores_used += s.cpu_cores_used
        self.pods += 1


def _percentile(values: list[Decimal], fraction: Decimal) -> Decimal:
    """Nearest-rank percentile on a list of Decimals.

    For a sample of n=14 and fraction=0.95, picks the
    ceil(0.95 * 14) = 14th element (i.e. max) — which is intentional:
    on small samples p95 collapses to max, and that's the conservative
    behaviour we want.
    """
    if not values:
        return Decimal(0)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    # Nearest-rank: rank = ceil(fraction * n), 1-indexed → 0-indexed = rank-1
    rank = int((fraction * Decimal(n)).to_integral_value(rounding="ROUND_CEILING"))
    rank = max(1, min(rank, n))
    return sorted_vals[rank - 1]


def _q(value: Decimal, places: int) -> str:
    """Quantize a Decimal to N places and return as string for JSON evidence.

    JSON-serializing Decimal as float would defeat our precision discipline;
    string keeps the exact representation.
    """
    quant = Decimal(1).scaleb(-places)
    return str(value.quantize(quant))


def _q_decimal(value: Decimal, places: int) -> Decimal:
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant)
