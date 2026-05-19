"""OOM-risk RAM rule.

Detects controllers whose actual RAM usage approaches their request,
indicating elevated risk of OOMKill on workload spikes.

Design (Stage 6.5):
  - Risk metric: per-day efficiency = sum(ram_bytes_used)/sum(ram_bytes_requested)
    aggregated across all pods of the controller for that day.
  - Trigger: p95(efficiency_per_day) >= 0.85 over the evaluation window.
  - Recommendation: increase RAM request to p95(used_bytes) * (1 + safety_margin).
  - monthly_saving_usd holds the "cost of safety" — the extra $/month required
    for the additional RAM (positive value, semantically an investment, not a saving).
  - Severity is computed by engine.severity_for from this $-impact.
  - DaemonSets included (RAM pressure affects them identically).
  - Unallocated rows skipped.
  - Targets with median(ram_bytes_requested) < 64 MiB are ignored as too small
    to be operationally interesting.
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
from app.services.recommendations.rules._thresholds import MIN_VALID_DAYS


# Tunables — module-level constants for now.
_EFFICIENCY_TRIGGER = Decimal("0.85")
_SAFETY_MARGIN = Decimal("0.30")
_MIN_DAYS_WITH_REQUEST = MIN_VALID_DAYS
_MIN_REQUEST_BYTES = Decimal(64 * 1024 * 1024)  # 64 MiB
_MONTHLY_HOURS = Decimal(720)
_GIB = Decimal(1024 * 1024 * 1024)
_P95_FRACTION = Decimal("0.95")


class OomRiskRamRule:
    rule_id: str = RuleId.OOM_RISK_RAM.value

    def evaluate(self, ctx: EvaluationContext) -> list[RuleFinding]:
        # Aggregate per-day, per-controller.
        by_target: dict[
            tuple[str, str, str],
            dict[date, _DayAccumulator],
        ] = defaultdict(lambda: defaultdict(_DayAccumulator))

        for s in ctx.snapshots:
            if s.controller == UNALLOCATED:
                continue
            key = (s.namespace, s.controller, s.controller_kind)
            by_target[key][s.bucket_date].add(s)

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
        valid_days = [d for d, acc in per_day.items() if acc.bytes_requested > 0]
        if len(valid_days) < _MIN_DAYS_WITH_REQUEST:
            return None

        bytes_requested_series = [per_day[d].bytes_requested for d in valid_days]
        bytes_used_series = [per_day[d].bytes_used for d in valid_days]
        pods_series = [per_day[d].pods for d in valid_days]

        bytes_requested_median = median(bytes_requested_series)
        if bytes_requested_median < _MIN_REQUEST_BYTES:
            return None

        # Per-day efficiency, then p95 across days.
        efficiency_series: list[Decimal] = []
        for req, used in zip(bytes_requested_series, bytes_used_series):
            if req > 0:
                efficiency_series.append(used / req)
        if not efficiency_series:
            return None

        efficiency_p95 = _percentile(efficiency_series, _P95_FRACTION)
        if efficiency_p95 < _EFFICIENCY_TRIGGER:
            return None

        bytes_used_p95 = _percentile(bytes_used_series, _P95_FRACTION)
        bytes_recommended = bytes_used_p95 * (Decimal(1) + _SAFETY_MARGIN)

        # If recommendation is BELOW current request, the rule shouldn't fire —
        # user is technically over-requesting on the absolute axis even though
        # efficiency is high. (Possible when used spikes high but median request
        # is also generous.) Skip — this isn't an OOM-risk case.
        bytes_delta = bytes_recommended - bytes_requested_median
        if bytes_delta <= 0:
            return None

        # Cost of safety: additional GiB-hours per month, priced at cluster's
        # empirical $/GiB-hour. ram_unit_cost_per_gib_hour comes from EvaluationContext.
        gib_delta = bytes_delta / _GIB
        monthly_cost_usd = gib_delta * ctx.ram_unit_cost_per_gib_hour * _MONTHLY_HOURS

        evidence = {
            "rule_version": "1.0",
            "days_evaluated": len(valid_days),
            "ram_requested_median_gib": _q(bytes_requested_median / _GIB, 4),
            "ram_used_p95_gib": _q(bytes_used_p95 / _GIB, 4),
            "ram_recommended_gib": _q(bytes_recommended / _GIB, 4),
            "ram_delta_gib": _q(gib_delta, 4),
            "efficiency_p95": _q(efficiency_p95, 4),
            "efficiency_trigger": str(_EFFICIENCY_TRIGGER),
            "safety_margin": str(_SAFETY_MARGIN),
            "ram_unit_cost_per_gib_hour": _q(ctx.ram_unit_cost_per_gib_hour, 8),
            "monthly_hours": int(_MONTHLY_HOURS),
            "controller_kind": controller_kind,
            "pods_per_day_avg": _q(
                sum(pods_series, Decimal(0)) / Decimal(len(pods_series)), 2
            ),
            "monthly_cost_of_safety_usd": _q(monthly_cost_usd, 4),
            "interpretation": "increase RAM requests to mitigate OOMKill risk",
        }

        return RuleFinding(
            target_kind=RecommendationTargetKind.CONTROLLER,
            target_namespace=namespace,
            target_controller=controller,
            monthly_saving_usd=_q_decimal(monthly_cost_usd, 4),
            evidence=evidence,
        )


# ─── Helpers ─────────────────────────────────────────────────────────────


class _DayAccumulator:
    __slots__ = ("bytes_requested", "bytes_used", "pods")

    def __init__(self) -> None:
        self.bytes_requested: Decimal = Decimal(0)
        self.bytes_used: Decimal = Decimal(0)
        self.pods: int = 0

    def add(self, s: CostSnapshot) -> None:
        self.bytes_requested += s.ram_bytes_requested
        self.bytes_used += s.ram_bytes_used
        self.pods += 1


def _percentile(values: list[Decimal], fraction: Decimal) -> Decimal:
    if not values:
        return Decimal(0)
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    rank = int((fraction * Decimal(n)).to_integral_value(rounding="ROUND_CEILING"))
    rank = max(1, min(rank, n))
    return sorted_vals[rank - 1]


def _q(value: Decimal, places: int) -> str:
    quant = Decimal(1).scaleb(-places)
    return str(value.quantize(quant))


def _q_decimal(value: Decimal, places: int) -> Decimal:
    quant = Decimal(1).scaleb(-places)
    return value.quantize(quant)
