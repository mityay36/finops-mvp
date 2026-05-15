from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ServiceCostBreakdown(BaseModel):
    service_name: str
    cost: Decimal
    share: float = Field(ge=0, le=1)


class BillingSummary(BaseModel):
    cluster_id: UUID
    period_start: datetime
    period_end: datetime
    currency: str
    total_cost: Decimal
    preemptible_cost: Decimal
    preemptible_share: float = Field(ge=0, le=1)
    by_service: list[ServiceCostBreakdown]


class TimeseriesPoint(BaseModel):
    timestamp: datetime
    cost: Decimal
    # Optional: present only when group_by=service
    service_name: str | None = None


class BillingTimeseries(BaseModel):
    cluster_id: UUID
    period_start: datetime
    period_end: datetime
    granularity: str
    group_by: str
    currency: str
    points: list[TimeseriesPoint]


class TopResource(BaseModel):
    resource_id: str | None
    resource_name: str | None
    service_name: str
    sku_name: str
    cost: Decimal
    is_preemptible: bool


class BillingTopResources(BaseModel):
    cluster_id: UUID
    period_start: datetime
    period_end: datetime
    currency: str
    items: list[TopResource]


class LatestSyncRun(BaseModel):
    """Lightweight view of the latest successful sync run for a cluster."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cluster_id: UUID
    finished_at: datetime
    records_imported: int
    window_start: datetime
    window_end: datetime
