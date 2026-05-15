"""Pydantic schemas for /allocations read API.

These response models are the contract with the frontend. They are intentionally
flat and explicit: every cost component has its own field, every metric is named.
We do NOT expose internal repository row types here — the API translates them.

Honesty layer: every response embeds CoverageInfo describing how complete the
data is for the requested period (missing days, partial days). Frontend MUST
render this — silently hiding gaps would mislead users about real costs.
"""

from datetime import date as date_type, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


GroupByDim = Literal["namespace", "controller", "node"]


class CostBreakdown(BaseModel):
    """All cost components for one cell of the response.

    Currency is whatever the OpenCost deployment is configured to emit
    (RUB for YC, USD for AWS, etc.). The API does no conversion.
    """
    model_config = ConfigDict(from_attributes=True)

    cpu: Decimal = Decimal(0)
    ram: Decimal = Decimal(0)
    gpu: Decimal = Decimal(0)
    pv: Decimal = Decimal(0)
    network: Decimal = Decimal(0)
    load_balancer: Decimal = Decimal(0)
    shared: Decimal = Decimal(0)
    external: Decimal = Decimal(0)
    total: Decimal = Decimal(0)


class CoverageInfo(BaseModel):
    """Honesty layer: how complete is the data backing this response.

    Three categories of days:
    - days_with_data:   days that have rows in cost_snapshots
    - missing_days:     days requested but absent from cost_snapshots
    - partial_days:     days present but known to be incomplete (today; the
                        oldest day in the window when it was captured mid-day)

    completeness_ratio is a single 0..1 number for UI badges:
        days_with_data / days_requested  (partial days count as 1.0)
    """
    requested_from: date_type
    requested_to: date_type
    days_requested: int
    days_with_data: int
    missing_days: list[date_type]
    partial_days: list[date_type] = Field(default_factory=list)
    completeness_ratio: float = Field(..., ge=0.0, le=1.0)


class AllocationsTotalsResponse(BaseModel):
    cluster_id: str
    period: CoverageInfo
    breakdown: CostBreakdown
    cpu_efficiency: float | None = Field(
        None,
        description="Cost-weighted average CPU efficiency over the period.",
    )
    ram_efficiency: float | None = Field(
        None,
        description="Cost-weighted average RAM efficiency over the period.",
    )
    generated_at: datetime


class AggregatedItem(BaseModel):
    key: str
    breakdown: CostBreakdown
    cpu_efficiency: float | None = None
    ram_efficiency: float | None = None
    share_of_total: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="This item's total / cluster total over the period.",
    )


class AllocationsAggregatedResponse(BaseModel):
    cluster_id: str
    period: CoverageInfo
    group_by: GroupByDim
    items: list[AggregatedItem]
    other: AggregatedItem | None = Field(
        None,
        description="Aggregate of keys beyond top-N. Null if no truncation.",
    )
    cluster_total: Decimal
    generated_at: datetime


class TimeseriesPointDTO(BaseModel):
    bucket_date: date_type
    key: str | None = None
    breakdown: CostBreakdown


class AllocationsTimeseriesResponse(BaseModel):
    cluster_id: str
    period: CoverageInfo
    group_by: GroupByDim | None = None
    series_keys: list[str] = Field(default_factory=list)
    points: list[TimeseriesPointDTO]
    generated_at: datetime
