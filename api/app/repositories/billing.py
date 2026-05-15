from datetime import datetime
from decimal import Decimal
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import and_, func, literal_column, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BillingRecord
from app.providers.dto import BillingRecordDTO




_RESOURCE_ID_UNKNOWN = "_unknown_"


class BillingRepository:
    """Bulk-insert billing records with idempotency on (cluster_id, period_start, resource_id, sku_name)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_batch(
        self,
        cluster_id: UUID,
        records: Iterable[BillingRecordDTO],
    ) -> int:
        """Insert a batch of DTOs. Returns the number of rows actually inserted
        (excluding rows skipped due to ON CONFLICT)."""
        rows = []
        for dto in records:
            rows.append(
                {
                    "cluster_id": cluster_id,
                    "period_start": dto.period_start,
                    "period_end": dto.period_end,
                    "service_name": dto.service_name,
                    "resource_id": dto.resource_id or _RESOURCE_ID_UNKNOWN,
                    "resource_name": dto.resource_name,
                    "sku_name": dto.sku_name,
                    "cost": dto.cost,
                    "currency": dto.currency,
                    "label_namespace": dto.label_namespace,
                    "label_service": dto.label_service,
                    "is_preemptible": dto.is_preemptible,
                }
            )

        if not rows:
            return 0

        stmt = insert(BillingRecord).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["cluster_id", "period_start", "resource_id", "sku_name"]
        )
        result = await self.session.execute(stmt)
        # rowcount under asyncpg with ON CONFLICT DO NOTHING returns the number
        # of actually inserted rows (not the number passed in).
        return result.rowcount or 0

    async def list_currencies(
        self,
        cluster_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> list[str]:
        stmt = (
            select(BillingRecord.currency)
            .where(BillingRecord.cluster_id == cluster_id)
            .where(BillingRecord.period_start >= period_start)
            .where(BillingRecord.period_start < period_end)
            .distinct()
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def summary_totals(
        self,
        cluster_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[Decimal, Decimal]:
        """Returns (total_cost, preemptible_cost) for the window."""
        stmt = select(
            func.coalesce(func.sum(BillingRecord.cost), 0),
            func.coalesce(
                func.sum(BillingRecord.cost).filter(BillingRecord.is_preemptible.is_(True)),
                0,
            ),
        ).where(
            and_(
                BillingRecord.cluster_id == cluster_id,
                BillingRecord.period_start >= period_start,
                BillingRecord.period_start < period_end,
            )
        )
        row = (await self.session.execute(stmt)).one()
        return Decimal(row[0]), Decimal(row[1])

    async def summary_by_service(
        self,
        cluster_id: UUID,
        period_start: datetime,
        period_end: datetime,
    ) -> list[tuple[str, Decimal]]:
        stmt = (
            select(
                BillingRecord.service_name,
                func.sum(BillingRecord.cost).label("cost"),
            )
            .where(
                and_(
                    BillingRecord.cluster_id == cluster_id,
                    BillingRecord.period_start >= period_start,
                    BillingRecord.period_start < period_end,
                )
            )
            .group_by(BillingRecord.service_name)
            .order_by(func.sum(BillingRecord.cost).desc())
        )
        return [(row[0], Decimal(row[1])) for row in (await self.session.execute(stmt)).all()]

    async def timeseries(
        self,
        cluster_id: UUID,
        period_start: datetime,
        period_end: datetime,
        granularity: str,  # 'day' | 'week'
        group_by_service: bool,
    ) -> list[tuple[datetime, str | None, Decimal]]:
        bucket = func.date_trunc(granularity, BillingRecord.period_start).label("bucket")
        cost_sum = func.sum(BillingRecord.cost).label("cost")

        columns = [bucket, cost_sum]
        group_cols = [bucket]
        order_cols = [bucket]
        if group_by_service:
            columns.insert(1, BillingRecord.service_name)
            group_cols.append(BillingRecord.service_name)
            order_cols.append(literal_column("cost").desc())

        stmt = (
            select(*columns)
            .where(
                and_(
                    BillingRecord.cluster_id == cluster_id,
                    BillingRecord.period_start >= period_start,
                    BillingRecord.period_start < period_end,
                )
            )
            .group_by(*group_cols)
            .order_by(*order_cols)
        )
        rows = (await self.session.execute(stmt)).all()
        if group_by_service:
            return [(r[0], r[1], Decimal(r[2])) for r in rows]
        return [(r[0], None, Decimal(r[1])) for r in rows]

    async def top_resources(
        self,
        cluster_id: UUID,
        period_start: datetime,
        period_end: datetime,
        limit: int,
    ) -> list[tuple[str | None, str | None, str, str, Decimal, bool]]:
        stmt = (
            select(
                BillingRecord.resource_id,
                func.max(BillingRecord.resource_name).label("resource_name"),
                BillingRecord.service_name,
                BillingRecord.sku_name,
                func.sum(BillingRecord.cost).label("cost"),
                func.bool_or(BillingRecord.is_preemptible).label("is_preemptible"),
            )
            .where(
                and_(
                    BillingRecord.cluster_id == cluster_id,
                    BillingRecord.period_start >= period_start,
                    BillingRecord.period_start < period_end,
                )
            )
            .group_by(
                BillingRecord.resource_id,
                BillingRecord.service_name,
                BillingRecord.sku_name,
            )
            .order_by(func.sum(BillingRecord.cost).desc())
            .limit(limit)
        )
        return [
            (r[0], r[1], r[2], r[3], Decimal(r[4]), bool(r[5]))
            for r in (await self.session.execute(stmt)).all()
        ]