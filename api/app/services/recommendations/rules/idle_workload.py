"""Idle workload rule.

Detects controllers that are running but effectively unused — both CPU
and RAM stay near baseline for the entire window. The recommended action
is "delete the workload"; saving equals the workload's full monthly cost.

Design (Stage 6.6):
  - Idle definition: p95(cpu_used) < 0.005 cores AND p95(ram_used) < 64 MiB.
    Both axes must be quiet — high RAM with zero CPU may be a legitimate
    in-memory cache, not idle.
  - Only deployment and statefulset controllers are considered. DaemonSets
    are by-design always-running per-node infra; CronJobs are idle by-design
    between runs; raw pods without controllers are out of scope.
  - System namespaces are whitelisted-out — recommending "delete kube-proxy"
    must never happen.
  - monthly_saving_usd = median(total_cost_per_day) × 30. Median tolerates
    one-day spikes (restart, image pull, GC).
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


# Tunables.
_CPU_IDLE_THRESHOLD_CORES = Decimal("0.005")           # 5 millicores
_RAM_IDLE_THRESHOLD_BYTES = Decimal(64 * 1024 * 1024)  # 64 MiB
_MIN_DAYS = 10
_MIN_MONTHLY_SAVING_USD = Decimal("5.00")
_DAYS_PER_MONTH = Decimal(30)
_GIB = Decimal(1024 * 1024 * 1024)
_P95_FRACTION = Decimal("0.95")

# Namespaces that must never receive an "idle, delete this" recommendation.
# These hold cluster infrastructure that is idle by-design (operators,
# webhooks, agents) and removing them breaks the cluster.
_SYSTEM_NAMESPACES: frozenset[str] = frozenset({
    "kube-system",
    "kube-public",
    "kube-node-lease",
    "opencost",
    "gatekeeper-system",
    "cattle-system",
    "ingress-nginx",
    "cert-manager",
})

# Controller kinds eligible for "delete the workload" advice.
_ELIGIBLE_KINDS: frozenset[str] = frozenset({"deployment", "statefulset"})


class IdleWorkloadRule:
    rule_id: str = RuleId.IDLE_WORKLOAD.value

    def evaluate(self, ctx: EvaluationContext) -> list[RuleFinding]:
        by_target: dict[
            tuple[str, str, str],
            dict[date, _DayAccumulator],
        ] = defaultdict(lambda: defaultdict(_DayAccumulator))

        for s in ctx.snapshots:
            if s.controller == UNALLOCATED:
                continue
            if s.namespace in _SYSTEM_NAMESPACES:
                continue
            if s.controller_kind not in _ELIGIBLE_KINDS:
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
        days = sorted(per_day.keys())
        if len(days) < _MIN_DAYS:
            return None

        cpu_used = [per_day[d].cpu_cores_used for d in days]
        ram_used = [per_day[d].ram_bytes_used for d in days]
        total_cost = [per_day[d].total_cost for d in days]
        pods = [per_day[d].pods for d in days]

        cpu_p95 = _percentile(cpu_used, _P95_FRACTION)
        ram_p95 = _percentile(ram_used, _P95_FRACTION)

        # Both axes must be idle — see rule docstring.
        if cpu_p95 >= _CPU_IDLE_THRESHOLD_CORES:
            return None
        if ram_p95 >= _RAM_IDLE_THRESHOLD_BYTES:
            return None

        daily_cost_median = median(total_cost)
        monthly_saving = daily_cost_median * _DAYS_PER_MONTH

        if monthly_saving < _MIN_MONTHLY_SAVING_USD:
            return None

        evidence = {
            "rule_version": "1.0",
            "days_evaluated": len(days),
            "cpu_used_p95_cores": _q(cpu_p95, 6),
            "ram_used_p95_gib": _q(ram_p95 / _GIB, 4),
            "cpu_idle_threshold_cores": str(_CPU_IDLE_THRESHOLD_CORES),
            "ram_idle_threshold_gib": _q(
                _RAM_IDLE_THRESHOLD_BYTES / _GIB, 4
            ),
            "daily_cost_median_usd": _q(daily_cost_median, 4),
            "controller_kind": controller_kind,
            "pods_per_day_avg": _q(
                sum(pods, Decimal(0)) / Decimal(len(pods)), 2
            ),
            "monthly_saving_usd": _q(monthly_saving, 4),
            "interpretation": "workload appears idle — consider deleting",
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
    __slots__ = ("cpu_cores_used", "ram_bytes_used", "total_cost", "pods")

    def __init__(self) -> None:
        self.cpu_cores_used: Decimal = Decimal(0)
        self.ram_bytes_used: Decimal = Decimal(0)
        self.total_cost: Decimal = Decimal(0)
        self.pods: int = 0

    def add(self, s: CostSnapshot) -> None:
        self.cpu_cores_used += s.cpu_cores_used
        self.ram_bytes_used += s.ram_bytes_used
        self.total_cost += s.total_cost
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
