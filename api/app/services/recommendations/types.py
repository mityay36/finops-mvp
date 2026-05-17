from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.models.recommendation import (
    RecommendationTargetKind,
)
from app.models.snapshot import CostSnapshot


# ─── Inputs ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EvaluationContext:
    """Everything a rule needs to evaluate, prepared once per engine run.

    The engine guarantees:
      - `snapshots` is restricted to a single cluster
      - `snapshots` covers exactly `bucket_dates` (no gaps from the rule's POV)
      - `bucket_dates` has at least `min_valid_days` entries; otherwise the
        engine short-circuits before invoking any rule
      - `cluster_monthly_cost` is the projection used for severity mapping
        and is the same value for every rule in this run
    """

    cluster_id: UUID
    bucket_dates: tuple[date, ...]
    snapshots: tuple[CostSnapshot, ...]
    cluster_monthly_cost: Decimal
    cpu_unit_cost_per_core_hour: Decimal
    ram_unit_cost_per_gib_hour: Decimal
    min_valid_days: int


# ─── Outputs ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RuleFinding:
    """What a rule emits when it fires for a given target.

    The engine maps this into a Recommendation row, supplying the cluster_id,
    rule_id (from the rule itself), severity (from saving / cluster cost),
    and lifecycle bookkeeping.
    """

    target_kind: RecommendationTargetKind
    target_namespace: str
    target_controller: str
    monthly_saving_usd: Decimal
    evidence: dict[str, Any] = field(default_factory=dict)


# ─── Rule contract ───────────────────────────────────────────────────────


class RuleEvaluator(Protocol):
    """A pure function: snapshots → findings.

    Implementations must:
      - Be stateless (no DB access, no I/O)
      - Be deterministic (same context → same findings)
      - Return at most one finding per (target_namespace, target_controller)
      - Set rule_id via the `rule_id` class attribute (not a method)
    """

    rule_id: str

    def evaluate(self, ctx: EvaluationContext) -> list[RuleFinding]: ...
