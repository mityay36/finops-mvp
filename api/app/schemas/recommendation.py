"""Pydantic schemas for the recommendations API.

Schemas are split between list-view (lighter, without evidence) and
detail-view (full evidence dict). monthly_impact_usd carries the
neutral $-magnitude; impact_kind tells the consumer how to render it
(saving vs cost-of-safety).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Maps ────────────────────────────────────────────────────────────────


# Per-rule semantic of monthly_saving_usd. New rules must register here
# (or, eventually, expose impact_kind as a class attribute on RuleEvaluator).
_RULE_IMPACT_KIND: dict[str, Literal["saving", "cost_of_safety"]] = {
    "rightsizing_cpu": "saving",
    "idle_workload": "saving",
    "oom_risk_ram": "cost_of_safety",
}


def impact_kind_for(rule_id: str) -> Literal["saving", "cost_of_safety"]:
    """Default to 'saving' for unknown rules — safer assumption for UI."""
    return _RULE_IMPACT_KIND.get(rule_id, "saving")


# ─── Item / Detail ───────────────────────────────────────────────────────


class RecommendationItem(BaseModel):
    """List-view shape — omits evidence to keep payload compact."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    rule_id: str
    target_kind: str
    target_namespace: str
    target_controller: str
    status: Literal["open", "applied", "dismissed", "closed_resolved"]
    severity: Literal["info", "warning", "critical"]

    monthly_impact_usd: Decimal = Field(
        ...,
        description=(
            "Absolute $-magnitude per month. Interpret via impact_kind:"
            " 'saving' = potential reduction; 'cost_of_safety' = required investment."
        ),
    )
    impact_kind: Literal["saving", "cost_of_safety"]

    first_seen_at: datetime
    last_seen_at: datetime
    resolved_at: datetime | None
    dismissed_reason: str | None


class RecommendationDetail(RecommendationItem):
    """Detail-view shape — full evidence dict included."""

    evidence: dict[str, Any]


# ─── List response with pagination metadata ─────────────────────────────


class PaginationMeta(BaseModel):
    total: int = Field(..., description="Total rows matching the filter set.")
    limit: int
    offset: int
    has_more: bool


class RecommendationListResponse(BaseModel):
    items: list[RecommendationItem]
    pagination: PaginationMeta


# ─── Lifecycle request bodies ────────────────────────────────────────────


class DismissRequest(BaseModel):
    """Reason is required and substantive — empty/whitespace strings rejected."""

    reason: str = Field(..., min_length=3, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("reason must contain at least 3 non-whitespace chars")
        return v


class RecommendationRefreshResponse(BaseModel):
    cluster_id: UUID
    accepted: bool
    message: str