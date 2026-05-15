"""Read-side service for cost allocations.

Sits between the repository (raw aggregations) and the router (HTTP shape).
Owns:
- period parsing & defaults (date_from/date_to → validated tuple)
- coverage computation (which days have data, which are missing/partial)
- top-N + 'other' assembly
- repository row → response DTO mapping

This service is stateless beyond the AsyncSession it holds.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.cost_snapshot import (
    AggregatedRow,
    CostSnapshotRepository,
    GroupByDim,
    TimeseriesPoint,
    TotalsRow,
)
from app.schemas.allocations import (
    AggregatedItem,
    AllocationsAggregatedResponse,
    AllocationsTimeseriesResponse,
    AllocationsTotalsResponse,
    CostBreakdown,
    CoverageInfo,
    TimeseriesPointDTO,
)


DEFAULT_WINDOW_DAYS = 30


class InvalidPeriodError(ValueError):
    """Raised when from/to params don't form a valid period."""


# ── Period helpers ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class Period:
    date_from: date
    date_to: date

    @property
    def days(self) -> int:
        return (self.date_to - self.date_from).days + 1


def resolve_period(
    *,
    date_from: date | None,
    date_to: date | None,
    default_window_days: int = DEFAULT_WINDOW_DAYS,
) -> Period:
    """Normalize (from, to) inputs.

    Rules:
    - both None → last N UTC days inclusive of today
    - exactly one None → 422 (caller raises HTTPException)
    - from > to → 422
    - to in the future relative to UTC today → clamped to today (we have no
      data after today, so silently clamp rather than 422)
    """
    if date_from is None and date_to is None:
        today = datetime.now(timezone.utc).date()
        return Period(
            date_from=today - timedelta(days=default_window_days - 1),
            date_to=today,
        )

    if date_from is None or date_to is None:
        raise InvalidPeriodError(
            "Provide both 'from' and 'to' query params, or neither."
        )

    if date_from > date_to:
        raise InvalidPeriodError("'from' must be <= 'to'.")

    today = datetime.now(timezone.utc).date()
    if date_to > today:
        date_to = today

    return Period(date_from=date_from, date_to=date_to)


# ── Coverage helpers ─────────────────────────────────────────────────────


def _build_coverage(
    *,
    period: Period,
    days_with_data: list[date],
) -> CoverageInfo:
    """Compute CoverageInfo from (period, days_with_data).

    partial_days = today (if present in days_with_data) and the earliest day
    in the window if it was captured by an OpenCost call whose lower bound
    was mid-day. Practically: we only mark today reliably as partial — the
    'old edge' case is rare in steady-state operation and would require us
    to track per-row capture timestamps. Future improvement.
    """
    requested_days = {
        period.date_from + timedelta(days=i) for i in range(period.days)
    }
    have = set(days_with_data)
    missing = sorted(requested_days - have)

    today = datetime.now(timezone.utc).date()
    partial: list[date] = [today] if today in have else []

    completeness = (
        (len(have) / len(requested_days)) if requested_days else 1.0
    )
    return CoverageInfo(
        requested_from=period.date_from,
        requested_to=period.date_to,
        days_requested=len(requested_days),
        days_with_data=len(have),
        missing_days=missing,
        partial_days=partial,
        completeness_ratio=round(completeness, 4),
    )


# ── Mappers: repo row → response DTO ─────────────────────────────────────


def _breakdown_from_totals(t: TotalsRow) -> CostBreakdown:
    return CostBreakdown(
        cpu=t.cpu_cost, ram=t.ram_cost, gpu=t.gpu_cost, pv=t.pv_cost,
        network=t.network_cost, load_balancer=t.load_balancer_cost,
        shared=t.shared_cost, external=t.external_cost, total=t.total_cost,
    )


def _breakdown_from_aggregated(r: AggregatedRow) -> CostBreakdown:
    return CostBreakdown(
        cpu=r.cpu_cost, ram=r.ram_cost, gpu=r.gpu_cost, pv=r.pv_cost,
        network=r.network_cost, load_balancer=r.load_balancer_cost,
        shared=r.shared_cost, external=r.external_cost, total=r.total_cost,
    )


def _breakdown_from_timeseries(p: TimeseriesPoint) -> CostBreakdown:
    return CostBreakdown(
        cpu=p.cpu_cost, ram=p.ram_cost, gpu=p.gpu_cost, pv=p.pv_cost,
        network=p.network_cost, load_balancer=p.load_balancer_cost,
        shared=p.shared_cost, external=p.external_cost, total=p.total_cost,
    )


def _safe_share(part: Decimal, whole: Decimal) -> float:
    if whole <= 0:
        return 0.0
    return round(float(part / whole), 6)


# ── Service ──────────────────────────────────────────────────────────────


class AllocationsQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CostSnapshotRepository(session)

    async def totals(
        self,
        cluster_id: UUID,
        *,
        period: Period,
    ) -> AllocationsTotalsResponse:
        totals = await self.repo.get_totals(
            cluster_id, date_from=period.date_from, date_to=period.date_to,
        )
        days = await self.repo.get_distinct_days(
            cluster_id, date_from=period.date_from, date_to=period.date_to,
        )
        coverage = _build_coverage(period=period, days_with_data=days)
        return AllocationsTotalsResponse(
            cluster_id=str(cluster_id),
            period=coverage,
            breakdown=_breakdown_from_totals(totals),
            cpu_efficiency=totals.cpu_efficiency,
            ram_efficiency=totals.ram_efficiency,
            generated_at=datetime.now(timezone.utc),
        )

    async def aggregated(
        self,
        cluster_id: UUID,
        *,
        period: Period,
        group_by: GroupByDim,
        top: int | None,
    ) -> AllocationsAggregatedResponse:
        # Fetch one over the requested top to detect whether truncation
        # would actually drop anything. If 'top' is None we fetch all.
        rows: list[AggregatedRow]
        if top is None:
            rows = await self.repo.get_aggregated(
                cluster_id, date_from=period.date_from, date_to=period.date_to,
                group_by=group_by, top=None,
            )
        else:
            rows = await self.repo.get_aggregated(
                cluster_id, date_from=period.date_from, date_to=period.date_to,
                group_by=group_by, top=top + 1,
            )

        # Cluster-wide total for share computation. Cheaper than re-aggregating.
        totals = await self.repo.get_totals(
            cluster_id, date_from=period.date_from, date_to=period.date_to,
        )
        cluster_total: Decimal = totals.total_cost

        days = await self.repo.get_distinct_days(
            cluster_id, date_from=period.date_from, date_to=period.date_to,
        )
        coverage = _build_coverage(period=period, days_with_data=days)

        truncated = top is not None and len(rows) > top
        kept_rows = rows[:top] if truncated else rows

        items = [
            AggregatedItem(
                key=r.key,
                breakdown=_breakdown_from_aggregated(r),
                cpu_efficiency=r.cpu_efficiency,
                ram_efficiency=r.ram_efficiency,
                share_of_total=_safe_share(r.total_cost, cluster_total),
            )
            for r in kept_rows
        ]

        other_item: AggregatedItem | None = None
        if truncated:
            # Compute "Other" from cluster total minus kept rows. This is
            # exact for total_cost but slightly approximated for component
            # breakdown — we sum components from a second repo call to get
            # exact figures, instead of subtracting Decimals (avoids
            # accumulating rounding error and missing 'other' efficiency).
            kept_keys = {r.key for r in kept_rows}
            all_rows = rows  # we already fetched top+1; for true 'other' we need all
            if len(rows) <= top + 1:
                # We only have one extra row beyond top; fetch the rest now.
                all_rows = await self.repo.get_aggregated(
                    cluster_id,
                    date_from=period.date_from,
                    date_to=period.date_to,
                    group_by=group_by,
                    top=None,
                )
            other_rows = [r for r in all_rows if r.key not in kept_keys]
            other_total = sum((r.total_cost for r in other_rows), Decimal(0))
            other_item = AggregatedItem(
                key="__other__",
                breakdown=CostBreakdown(
                    cpu=sum((r.cpu_cost for r in other_rows), Decimal(0)),
                    ram=sum((r.ram_cost for r in other_rows), Decimal(0)),
                    gpu=sum((r.gpu_cost for r in other_rows), Decimal(0)),
                    pv=sum((r.pv_cost for r in other_rows), Decimal(0)),
                    network=sum((r.network_cost for r in other_rows), Decimal(0)),
                    load_balancer=sum(
                        (r.load_balancer_cost for r in other_rows), Decimal(0)
                    ),
                    shared=sum((r.shared_cost for r in other_rows), Decimal(0)),
                    external=sum(
                        (r.external_cost for r in other_rows), Decimal(0)
                    ),
                    total=other_total,
                ),
                cpu_efficiency=None,  # weighted avg across heterogeneous keys is misleading
                ram_efficiency=None,
                share_of_total=_safe_share(other_total, cluster_total),
            )

        return AllocationsAggregatedResponse(
            cluster_id=str(cluster_id),
            period=coverage,
            group_by=group_by,
            items=items,
            other=other_item,
            cluster_total=cluster_total,
            generated_at=datetime.now(timezone.utc),
        )

    async def timeseries(
        self,
        cluster_id: UUID,
        *,
        period: Period,
        group_by: GroupByDim | None,
        top: int | None,
    ) -> AllocationsTimeseriesResponse:
        days = await self.repo.get_distinct_days(
            cluster_id, date_from=period.date_from, date_to=period.date_to,
        )
        coverage = _build_coverage(period=period, days_with_data=days)
        now = datetime.now(timezone.utc)

        if group_by is None:
            ts = await self.repo.get_timeseries_total(
                cluster_id,
                date_from=period.date_from,
                date_to=period.date_to,
            )
            points = [
                TimeseriesPointDTO(
                    bucket_date=p.bucket_date,
                    key=None,
                    breakdown=_breakdown_from_timeseries(p),
                )
                for p in ts
            ]
            return AllocationsTimeseriesResponse(
                cluster_id=str(cluster_id),
                period=coverage,
                group_by=None,
                series_keys=[],
                points=points,
                generated_at=now,
            )

        # Grouped: pick the top-N keys by total over the period, then ask the
        # repo for daily breakdown restricted to those keys. Days × keys.
        top_rows = await self.repo.get_aggregated(
            cluster_id,
            date_from=period.date_from,
            date_to=period.date_to,
            group_by=group_by,
            top=top,
        )
        keys = [r.key for r in top_rows]
        if not keys:
            return AllocationsTimeseriesResponse(
                cluster_id=str(cluster_id),
                period=coverage,
                group_by=group_by,
                series_keys=[],
                points=[],
                generated_at=now,
            )

        ts = await self.repo.get_timeseries_grouped(
            cluster_id,
            date_from=period.date_from,
            date_to=period.date_to,
            group_by=group_by,
            keys=keys,
        )
        points = [
            TimeseriesPointDTO(
                bucket_date=p.bucket_date,
                key=p.key,
                breakdown=_breakdown_from_timeseries(p),
            )
            for p in ts
        ]
        return AllocationsTimeseriesResponse(
            cluster_id=str(cluster_id),
            period=coverage,
            group_by=group_by,
            series_keys=keys,
            points=points,
            generated_at=now,
        )
