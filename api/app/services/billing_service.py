from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.billing import BillingRepository
from app.schemas import (
    BillingSummary,
    BillingTimeseries,
    BillingTopResources,
    ServiceCostBreakdown,
    TimeseriesPoint,
    TopResource,
)

_DEFAULT_LOOKBACK_DAYS = 30
_GRANULARITY_PG_MAP = {"daily": "day", "weekly": "week"}
_GROUP_BY_VALID = {"total", "service"}


class BillingValidationError(Exception):
    pass


class MultipleCurrenciesError(BillingValidationError):
    pass


class BillingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = BillingRepository(session)

    @staticmethod
    def _resolve_window(
        period_start: datetime | None, period_end: datetime | None
    ) -> tuple[datetime, datetime]:
        now = datetime.now(timezone.utc)
        end = period_end or now
        start = period_start or (end - timedelta(days=_DEFAULT_LOOKBACK_DAYS))
        if end <= start:
            raise BillingValidationError("period_end must be greater than period_start")
        # Normalize naive datetimes to UTC for safety.
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        return start, end

    async def _resolve_currency(
        self, cluster_id: UUID, start: datetime, end: datetime
    ) -> str:
        currencies = await self.repo.list_currencies(cluster_id, start, end)
        if not currencies:
            return "RUB"
        if len(currencies) > 1:
            raise MultipleCurrenciesError(
                f"Window contains multiple currencies: {sorted(currencies)}. "
                "Cross-currency aggregation is not supported."
            )
        return currencies[0]

    async def get_summary(
        self,
        cluster_id: UUID,
        period_start: datetime | None,
        period_end: datetime | None,
    ) -> BillingSummary:
        start, end = self._resolve_window(period_start, period_end)
        currency = await self._resolve_currency(cluster_id, start, end)

        total, preemptible = await self.repo.summary_totals(cluster_id, start, end)
        by_service_rows = await self.repo.summary_by_service(cluster_id, start, end)

        share = float(preemptible / total) if total > 0 else 0.0
        by_service = [
            ServiceCostBreakdown(
                service_name=name,
                cost=cost,
                share=float(cost / total) if total > 0 else 0.0,
            )
            for name, cost in by_service_rows
        ]

        return BillingSummary(
            cluster_id=cluster_id,
            period_start=start,
            period_end=end,
            currency=currency,
            total_cost=total,
            preemptible_cost=preemptible,
            preemptible_share=share,
            by_service=by_service,
        )

    async def get_timeseries(
        self,
        cluster_id: UUID,
        period_start: datetime | None,
        period_end: datetime | None,
        granularity: str,
        group_by: str,
    ) -> BillingTimeseries:
        if granularity not in _GRANULARITY_PG_MAP:
            raise BillingValidationError(
                f"granularity must be one of {sorted(_GRANULARITY_PG_MAP)}"
            )
        if group_by not in _GROUP_BY_VALID:
            raise BillingValidationError(
                f"group_by must be one of {sorted(_GROUP_BY_VALID)}"
            )

        start, end = self._resolve_window(period_start, period_end)
        currency = await self._resolve_currency(cluster_id, start, end)
        rows = await self.repo.timeseries(
            cluster_id,
            start,
            end,
            granularity=_GRANULARITY_PG_MAP[granularity],
            group_by_service=(group_by == "service"),
        )
        points = [
            TimeseriesPoint(timestamp=ts, service_name=svc, cost=cost)
            for ts, svc, cost in rows
        ]
        return BillingTimeseries(
            cluster_id=cluster_id,
            period_start=start,
            period_end=end,
            granularity=granularity,
            group_by=group_by,
            currency=currency,
            points=points,
        )

    async def get_top_resources(
        self,
        cluster_id: UUID,
        period_start: datetime | None,
        period_end: datetime | None,
        limit: int,
    ) -> BillingTopResources:
        start, end = self._resolve_window(period_start, period_end)
        currency = await self._resolve_currency(cluster_id, start, end)
        rows = await self.repo.top_resources(cluster_id, start, end, limit)
        items = [
            TopResource(
                resource_id=rid,
                resource_name=rname,
                service_name=svc,
                sku_name=sku,
                cost=cost,
                is_preemptible=preempt,
            )
            for rid, rname, svc, sku, cost, preempt in rows
        ]
        return BillingTopResources(
            cluster_id=cluster_id,
            period_start=start,
            period_end=end,
            currency=currency,
            items=items,
        )
