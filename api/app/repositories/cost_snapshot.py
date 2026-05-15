from __future__ import annotations

from datetime import date, datetime
from typing import Iterable
from uuid import UUID


from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Sequence


from sqlalchemy import Numeric, cast, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AllocationsSnapshotRun,
    CostSnapshot,
    SnapshotRunStatus,
)

# Upsert in chunks to keep statement size sane and avoid hitting Postgres
# parameter limits (default ~32k bound parameters per stmt).
_UPSERT_CHUNK = 500
# ── Public group-by dimensions exposed via API ───────────────────────────
GroupByDim = Literal["namespace", "controller", "node"]

# Map dimension name → SQLAlchemy column. Centralizing this prevents the API
# layer from injecting arbitrary column names into ORDER BY / GROUP BY.
_GROUP_COLUMNS = {
    "namespace": CostSnapshot.namespace,
    "controller": CostSnapshot.controller,
    "node": CostSnapshot.node,
}


@dataclass(frozen=True)
class AggregatedRow:
    """One row in an aggregated breakdown (group_by × cost components)."""
    key: str
    cpu_cost: Decimal
    ram_cost: Decimal
    gpu_cost: Decimal
    pv_cost: Decimal
    network_cost: Decimal
    load_balancer_cost: Decimal
    shared_cost: Decimal
    external_cost: Decimal
    total_cost: Decimal
    cpu_efficiency: float | None
    ram_efficiency: float | None


@dataclass(frozen=True)
class TotalsRow:
    """Aggregated totals for a cluster over a date range."""
    cpu_cost: Decimal
    ram_cost: Decimal
    gpu_cost: Decimal
    pv_cost: Decimal
    network_cost: Decimal
    load_balancer_cost: Decimal
    shared_cost: Decimal
    external_cost: Decimal
    total_cost: Decimal
    cpu_efficiency: float | None
    ram_efficiency: float | None
    days_covered: int


@dataclass(frozen=True)
class TimeseriesPoint:
    """One bucket on a daily timeseries."""
    bucket_date: date
    key: str | None  # None for cluster-wide series; namespace/etc for grouped
    cpu_cost: Decimal
    ram_cost: Decimal
    gpu_cost: Decimal
    pv_cost: Decimal
    network_cost: Decimal
    load_balancer_cost: Decimal
    shared_cost: Decimal
    external_cost: Decimal
    total_cost: Decimal


class CostSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_batch(self, rows: Iterable[dict]) -> int:
        """Upsert allocation rows.

        Each row must contain all unique-key fields and at minimum the
        cost fields. Returns total number of upserted rows.
        """
        all_rows = list(rows)
        if not all_rows:
            return 0

        affected = 0
        for start in range(0, len(all_rows), _UPSERT_CHUNK):
            chunk = all_rows[start : start + _UPSERT_CHUNK]
            stmt = pg_insert(CostSnapshot.__table__).values(chunk)

            update_cols = {
                col.name: stmt.excluded[col.name]
                for col in CostSnapshot.__table__.columns
                if col.name
                not in {
                    "id",
                    "cluster_id",
                    "bucket_date",
                    "namespace",
                    "controller",
                    "pod",
                    "node",
                }
            }

            stmt = stmt.on_conflict_do_update(
                constraint="uq_cost_snapshots_alloc_day",
                set_=update_cols,
            )
            result = await self.session.execute(stmt)
            affected += result.rowcount or len(chunk)

        return affected

    async def latest_bucket_date(self, cluster_id: UUID) -> date | None:
        stmt = select(func.max(CostSnapshot.bucket_date)).where(
            CostSnapshot.cluster_id == cluster_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_totals(
        self,
        cluster_id: UUID,
        *,
        date_from: date,
        date_to: date,
    ) -> TotalsRow:
        """Sum all cost components across [date_from, date_to] inclusive.

        Efficiency is a weighted average: sum(cost * efficiency) / sum(cost).
        Specifically, cpu_efficiency is weighted by cpu_cost; ram by ram_cost.
        Pods with NULL efficiency are excluded from the weighted average for
        that resource (they contribute 0 to both numerator and denominator).
        """
        # Weighted-efficiency expression: SUM(cpu_cost * cpu_eff) / NULLIF(SUM(cpu_cost where eff IS NOT NULL), 0)
        cpu_eff_num = func.sum(
            CostSnapshot.cpu_cost * cast(CostSnapshot.cpu_efficiency, Numeric(18, 6))
        ).filter(CostSnapshot.cpu_efficiency.is_not(None))
        cpu_eff_den = func.sum(CostSnapshot.cpu_cost).filter(
            CostSnapshot.cpu_efficiency.is_not(None)
        )
        ram_eff_num = func.sum(
            CostSnapshot.ram_cost * cast(CostSnapshot.ram_efficiency, Numeric(18, 6))
        ).filter(CostSnapshot.ram_efficiency.is_not(None))
        ram_eff_den = func.sum(CostSnapshot.ram_cost).filter(
            CostSnapshot.ram_efficiency.is_not(None)
        )

        stmt = select(
            func.coalesce(func.sum(CostSnapshot.cpu_cost), 0).label("cpu"),
            func.coalesce(func.sum(CostSnapshot.ram_cost), 0).label("ram"),
            func.coalesce(func.sum(CostSnapshot.gpu_cost), 0).label("gpu"),
            func.coalesce(func.sum(CostSnapshot.pv_cost), 0).label("pv"),
            func.coalesce(func.sum(CostSnapshot.network_cost), 0).label("net"),
            func.coalesce(func.sum(CostSnapshot.load_balancer_cost), 0).label("lb"),
            func.coalesce(func.sum(CostSnapshot.shared_cost), 0).label("shared"),
            func.coalesce(func.sum(CostSnapshot.external_cost), 0).label("external"),
            func.coalesce(func.sum(CostSnapshot.total_cost), 0).label("total"),
            (cpu_eff_num / func.nullif(cpu_eff_den, 0)).label("cpu_eff"),
            (ram_eff_num / func.nullif(ram_eff_den, 0)).label("ram_eff"),
            func.count(func.distinct(CostSnapshot.bucket_date)).label("days"),
        ).where(
            CostSnapshot.cluster_id == cluster_id,
            CostSnapshot.bucket_date >= date_from,
            CostSnapshot.bucket_date <= date_to,
        )

        row = (await self.session.execute(stmt)).one()
        return TotalsRow(
            cpu_cost=Decimal(row.cpu or 0),
            ram_cost=Decimal(row.ram or 0),
            gpu_cost=Decimal(row.gpu or 0),
            pv_cost=Decimal(row.pv or 0),
            network_cost=Decimal(row.net or 0),
            load_balancer_cost=Decimal(row.lb or 0),
            shared_cost=Decimal(row.shared or 0),
            external_cost=Decimal(row.external or 0),
            total_cost=Decimal(row.total or 0),
            cpu_efficiency=float(row.cpu_eff) if row.cpu_eff is not None else None,
            ram_efficiency=float(row.ram_eff) if row.ram_eff is not None else None,
            days_covered=int(row.days or 0),
        )

    async def get_aggregated(
        self,
        cluster_id: UUID,
        *,
        date_from: date,
        date_to: date,
        group_by: GroupByDim,
        top: int | None = None,
    ) -> list[AggregatedRow]:
        """Group cost rows by namespace | controller | node, sum components.

        `top` limits to N highest-total rows. Pass None to return all.
        Sort is always by total_cost DESC; tie-broken by key for determinism.
        """
        column = _GROUP_COLUMNS[group_by]

        cpu_eff_num = func.sum(
            CostSnapshot.cpu_cost * cast(CostSnapshot.cpu_efficiency, Numeric(18, 6))
        ).filter(CostSnapshot.cpu_efficiency.is_not(None))
        cpu_eff_den = func.sum(CostSnapshot.cpu_cost).filter(
            CostSnapshot.cpu_efficiency.is_not(None)
        )
        ram_eff_num = func.sum(
            CostSnapshot.ram_cost * cast(CostSnapshot.ram_efficiency, Numeric(18, 6))
        ).filter(CostSnapshot.ram_efficiency.is_not(None))
        ram_eff_den = func.sum(CostSnapshot.ram_cost).filter(
            CostSnapshot.ram_efficiency.is_not(None)
        )

        stmt = (
            select(
                column.label("key"),
                func.coalesce(func.sum(CostSnapshot.cpu_cost), 0).label("cpu"),
                func.coalesce(func.sum(CostSnapshot.ram_cost), 0).label("ram"),
                func.coalesce(func.sum(CostSnapshot.gpu_cost), 0).label("gpu"),
                func.coalesce(func.sum(CostSnapshot.pv_cost), 0).label("pv"),
                func.coalesce(func.sum(CostSnapshot.network_cost), 0).label("net"),
                func.coalesce(func.sum(CostSnapshot.load_balancer_cost), 0).label("lb"),
                func.coalesce(func.sum(CostSnapshot.shared_cost), 0).label("shared"),
                func.coalesce(func.sum(CostSnapshot.external_cost), 0).label("external"),
                func.coalesce(func.sum(CostSnapshot.total_cost), 0).label("total"),
                (cpu_eff_num / func.nullif(cpu_eff_den, 0)).label("cpu_eff"),
                (ram_eff_num / func.nullif(ram_eff_den, 0)).label("ram_eff"),
            )
            .where(
                CostSnapshot.cluster_id == cluster_id,
                CostSnapshot.bucket_date >= date_from,
                CostSnapshot.bucket_date <= date_to,
            )
            .group_by(column)
            .order_by(func.sum(CostSnapshot.total_cost).desc(), column.asc())
        )
        if top is not None:
            stmt = stmt.limit(top)

        rows = (await self.session.execute(stmt)).all()
        return [
            AggregatedRow(
                key=str(r.key),
                cpu_cost=Decimal(r.cpu or 0),
                ram_cost=Decimal(r.ram or 0),
                gpu_cost=Decimal(r.gpu or 0),
                pv_cost=Decimal(r.pv or 0),
                network_cost=Decimal(r.net or 0),
                load_balancer_cost=Decimal(r.lb or 0),
                shared_cost=Decimal(r.shared or 0),
                external_cost=Decimal(r.external or 0),
                total_cost=Decimal(r.total or 0),
                cpu_efficiency=float(r.cpu_eff) if r.cpu_eff is not None else None,
                ram_efficiency=float(r.ram_eff) if r.ram_eff is not None else None,
            )
            for r in rows
        ]

    async def get_timeseries_total(
        self,
        cluster_id: UUID,
        *,
        date_from: date,
        date_to: date,
    ) -> list[TimeseriesPoint]:
        """Daily total cost timeseries across the entire cluster.

        Returns one point per bucket_date that has rows. Days with no data are
        omitted — the API layer is responsible for explicitly representing gaps
        (we don't fabricate zero-rows for missing days; missing data is real).
        """
        stmt = (
            select(
                CostSnapshot.bucket_date,
                func.sum(CostSnapshot.cpu_cost).label("cpu"),
                func.sum(CostSnapshot.ram_cost).label("ram"),
                func.sum(CostSnapshot.gpu_cost).label("gpu"),
                func.sum(CostSnapshot.pv_cost).label("pv"),
                func.sum(CostSnapshot.network_cost).label("net"),
                func.sum(CostSnapshot.load_balancer_cost).label("lb"),
                func.sum(CostSnapshot.shared_cost).label("shared"),
                func.sum(CostSnapshot.external_cost).label("external"),
                func.sum(CostSnapshot.total_cost).label("total"),
            )
            .where(
                CostSnapshot.cluster_id == cluster_id,
                CostSnapshot.bucket_date >= date_from,
                CostSnapshot.bucket_date <= date_to,
            )
            .group_by(CostSnapshot.bucket_date)
            .order_by(CostSnapshot.bucket_date.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            TimeseriesPoint(
                bucket_date=r.bucket_date,
                key=None,
                cpu_cost=Decimal(r.cpu or 0),
                ram_cost=Decimal(r.ram or 0),
                gpu_cost=Decimal(r.gpu or 0),
                pv_cost=Decimal(r.pv or 0),
                network_cost=Decimal(r.net or 0),
                load_balancer_cost=Decimal(r.lb or 0),
                shared_cost=Decimal(r.shared or 0),
                external_cost=Decimal(r.external or 0),
                total_cost=Decimal(r.total or 0),
            )
            for r in rows
        ]

    async def get_timeseries_grouped(
        self,
        cluster_id: UUID,
        *,
        date_from: date,
        date_to: date,
        group_by: GroupByDim,
        keys: Sequence[str],
    ) -> list[TimeseriesPoint]:
        """Daily timeseries broken down by a group_by dimension, restricted to
        the given keys (typically: result of get_aggregated(top=N)).

        Caller passes the exact list of keys to render — this gives the API
        layer full control over "Top N + Other" computation. Repository stays
        a pure data-access layer; business logic for top-N stays out.
        """
        if not keys:
            return []

        column = _GROUP_COLUMNS[group_by]

        stmt = (
            select(
                CostSnapshot.bucket_date,
                column.label("key"),
                func.sum(CostSnapshot.cpu_cost).label("cpu"),
                func.sum(CostSnapshot.ram_cost).label("ram"),
                func.sum(CostSnapshot.gpu_cost).label("gpu"),
                func.sum(CostSnapshot.pv_cost).label("pv"),
                func.sum(CostSnapshot.network_cost).label("net"),
                func.sum(CostSnapshot.load_balancer_cost).label("lb"),
                func.sum(CostSnapshot.shared_cost).label("shared"),
                func.sum(CostSnapshot.external_cost).label("external"),
                func.sum(CostSnapshot.total_cost).label("total"),
            )
            .where(
                CostSnapshot.cluster_id == cluster_id,
                CostSnapshot.bucket_date >= date_from,
                CostSnapshot.bucket_date <= date_to,
                column.in_(list(keys)),
            )
            .group_by(CostSnapshot.bucket_date, column)
            .order_by(CostSnapshot.bucket_date.asc(), column.asc())
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            TimeseriesPoint(
                bucket_date=r.bucket_date,
                key=str(r.key),
                cpu_cost=Decimal(r.cpu or 0),
                ram_cost=Decimal(r.ram or 0),
                gpu_cost=Decimal(r.gpu or 0),
                pv_cost=Decimal(r.pv or 0),
                network_cost=Decimal(r.net or 0),
                load_balancer_cost=Decimal(r.lb or 0),
                shared_cost=Decimal(r.shared or 0),
                external_cost=Decimal(r.external or 0),
                total_cost=Decimal(r.total or 0),
            )
            for r in rows
        ]

    async def get_distinct_days(
        self,
        cluster_id: UUID,
        *,
        date_from: date,
        date_to: date,
    ) -> list[date]:
        """Return sorted list of bucket_dates that have data in the window.

        Used by the API to compute coverage gaps (which days the user requested
        but we don't have data for) — important for dashboard honesty.
        """
        stmt = (
            select(CostSnapshot.bucket_date)
            .where(
                CostSnapshot.cluster_id == cluster_id,
                CostSnapshot.bucket_date >= date_from,
                CostSnapshot.bucket_date <= date_to,
            )
            .group_by(CostSnapshot.bucket_date)
            .order_by(CostSnapshot.bucket_date.asc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)


class AllocationsSnapshotRunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        cluster_id: UUID,
        trigger: str,
        window_start: datetime,
        window_end: datetime,
    ) -> AllocationsSnapshotRun:
        run = AllocationsSnapshotRun(
            cluster_id=cluster_id,
            status=SnapshotRunStatus.RUNNING.value,
            trigger=trigger,
            window_start=window_start,
            window_end=window_end,
        )
        self.session.add(run)
        await self.session.flush()
        return run

    async def mark_success(
        self,
        run: AllocationsSnapshotRun,
        days_processed: int,
        rows_upserted: int,
    ) -> None:
        run.status = SnapshotRunStatus.SUCCESS.value
        run.days_processed = days_processed
        run.rows_upserted = rows_upserted
        run.finished_at = datetime.utcnow()
        await self.session.flush()

    async def mark_failed(
        self, run: AllocationsSnapshotRun, error: str
    ) -> None:
        run.status = SnapshotRunStatus.FAILED.value
        run.error = error[:2000]
        run.finished_at = datetime.utcnow()
        await self.session.flush()

    async def get_last_for_cluster(
        self, cluster_id: UUID
    ) -> AllocationsSnapshotRun | None:
        stmt = (
            select(AllocationsSnapshotRun)
            .where(AllocationsSnapshotRun.cluster_id == cluster_id)
            .order_by(AllocationsSnapshotRun.started_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_cluster(
        self, cluster_id: UUID, *, limit: int, offset: int
    ) -> tuple[list[AllocationsSnapshotRun], int]:
        total_stmt = (
            select(func.count())
            .select_from(AllocationsSnapshotRun)
            .where(AllocationsSnapshotRun.cluster_id == cluster_id)
        )
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(AllocationsSnapshotRun)
            .where(AllocationsSnapshotRun.cluster_id == cluster_id)
            .order_by(AllocationsSnapshotRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows), total