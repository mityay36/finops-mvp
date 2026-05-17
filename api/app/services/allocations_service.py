# app/services/allocations_service.py
import re
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.clients import OpenCostClient, OpenCostInternalError
from app.schemas.allocations import (
    AllocationsTotalsResponse,
    CostBreakdown,
    CoverageInfo,
)
from app.services.cluster_service import ClusterService
from app.services.factory import ServiceFactory

logger = logging.getLogger(__name__)

_WINDOW_PATTERN = re.compile(
    r"^(\d+[hdwm]"
    r"|today|yesterday|week|month|lastweek|lastmonth"
    r"|\d{4}-\d{2}-\d{2}T[\d:.]+Z?,\d{4}-\d{2}-\d{2}T[\d:.]+Z?)$"
)
_STEP_PATTERN = re.compile(r"^\d+[hdwm]$")
_AGGREGATE_VALID = {"namespace", "controller", "pod", "node", "cluster", "label"}


class AllocationsValidationError(Exception): ...


class OpenCostNotConfiguredError(Exception): ...


class OpenCostUnavailableError(Exception): ...


# ---------- internal DTOs (NOT exported via schemas) ----------


@dataclass
class _InternalResources:
    cpu: Decimal = Decimal(0)
    ram: Decimal = Decimal(0)
    gpu: Decimal = Decimal(0)
    pv: Decimal = Decimal(0)
    network: Decimal = Decimal(0)
    load_balancer: Decimal = Decimal(0)
    shared: Decimal = Decimal(0)
    external: Decimal = Decimal(0)

    @property
    def total(self) -> Decimal:
        return (
            self.cpu
            + self.ram
            + self.gpu
            + self.pv
            + self.network
            + self.load_balancer
            + self.shared
            + self.external
        )


@dataclass
class _InternalAllocation:
    name: str
    namespace: str | None
    controller: str | None
    controller_kind: str | None
    pod: str | None
    node: str | None
    cluster: str | None
    window_start: datetime
    window_end: datetime
    minutes: float
    resources: _InternalResources
    cpu_efficiency: float | None
    ram_efficiency: float | None

    @property
    def total_cost(self) -> Decimal:
        return self.resources.total


# ---------- service ----------


class AllocationsService:
    def __init__(self, session: AsyncSession, service_factory: ServiceFactory) -> None:
        self.session = session
        self.factory = service_factory
        self.cluster_service = ClusterService(session)

    @staticmethod
    def _validate_query(window: str, aggregate: str, step: str | None) -> None:
        if not _WINDOW_PATTERN.match(window):
            raise AllocationsValidationError(
                "window must be like '7d', '24h', 'month', or RFC3339 pair"
            )
        if aggregate not in _AGGREGATE_VALID:
            raise AllocationsValidationError(
                f"aggregate must be one of {sorted(_AGGREGATE_VALID)}"
            )
        if step is not None and not _STEP_PATTERN.match(step):
            raise AllocationsValidationError("step must be like '1d' or '6h'")

    @staticmethod
    def _parse_time(value: str | None) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _to_decimal(value: object) -> Decimal:
        if value is None:
            return Decimal(0)
        try:
            return Decimal(str(value))
        except (ValueError, ArithmeticError):
            return Decimal(0)

    @classmethod
    def _normalize(cls, raw: dict) -> _InternalAllocation:
        props = raw.get("properties") or {}
        window = raw.get("window") or {}
        resources = _InternalResources(
            cpu=cls._to_decimal(raw.get("cpuCost")),
            ram=cls._to_decimal(raw.get("ramCost")),
            gpu=cls._to_decimal(raw.get("gpuCost")),
            pv=cls._to_decimal(raw.get("pvCost")),
            network=cls._to_decimal(raw.get("networkCost")),
            load_balancer=cls._to_decimal(raw.get("loadBalancerCost")),
            shared=cls._to_decimal(raw.get("sharedCost")),
            external=cls._to_decimal(raw.get("externalCost")),
        )
        return _InternalAllocation(
            name=raw.get("_name") or props.get("name") or "unknown",
            namespace=props.get("namespace"),
            controller=props.get("controller"),
            controller_kind=props.get("controllerKind"),
            pod=props.get("pod"),
            node=props.get("node"),
            cluster=props.get("cluster"),
            window_start=cls._parse_time(window.get("start")),
            window_end=cls._parse_time(window.get("end")),
            minutes=float(raw.get("minutes") or 0.0),
            resources=resources,
            cpu_efficiency=raw.get("cpuEfficiency"),
            ram_efficiency=raw.get("ramEfficiency"),
        )

    @staticmethod
    def _sum_breakdown(items: list[_InternalAllocation]) -> CostBreakdown:
        cpu = ram = gpu = pv = net = lb = shared = ext = Decimal(0)
        for a in items:
            r = a.resources
            cpu += r.cpu
            ram += r.ram
            gpu += r.gpu
            pv += r.pv
            net += r.network
            lb += r.load_balancer
            shared += r.shared
            ext += r.external
        total = cpu + ram + gpu + pv + net + lb + shared + ext
        return CostBreakdown(
            cpu=cpu,
            ram=ram,
            gpu=gpu,
            pv=pv,
            network=net,
            load_balancer=lb,
            shared=shared,
            external=ext,
            total=total,
        )

    @staticmethod
    def _weighted_efficiency(
        items: list[_InternalAllocation],
        kind: str,
    ) -> float | None:
        weighted = Decimal(0)
        weight = Decimal(0)
        for a in items:
            value = a.cpu_efficiency if kind == "cpu" else a.ram_efficiency
            if value is None:
                continue
            cost = a.resources.cpu if kind == "cpu" else a.resources.ram
            if cost <= 0:
                continue
            weighted += Decimal(str(value)) * cost
            weight += cost
        if weight == 0:
            return None
        return float(weighted / weight)

    @staticmethod
    def _coverage_from_window(
        items: list[_InternalAllocation],
        window: str,
    ) -> CoverageInfo:
        # Минимальная честная реализация: берём min/max из реальных данных,
        # либо «сегодня» если данных нет. Остальное проставляем нулями.
        if items:
            start = min(a.window_start for a in items).date()
            end = max(a.window_end for a in items).date()
        else:
            today = datetime.now(timezone.utc).date()
            start = end = today
        days_requested = max((end - start).days + 1, 1)
        days_with_data = days_requested if items else 0
        ratio = (days_with_data / days_requested) if days_requested else 0.0
        return CoverageInfo(
            requested_from=start,
            requested_to=end,
            days_requested=days_requested,
            days_with_data=days_with_data,
            missing_days=[],
            partial_days=[],
            completeness_ratio=ratio,
        )

    async def list_allocations(
        self,
        cluster_id: UUID,
        window: str,
        aggregate: str,
        step: str | None,
        limit: int,
    ) -> AllocationsTotalsResponse:
        self._validate_query(window, aggregate, step)
        cluster = await self.cluster_service.get_cluster(cluster_id)

        if not cluster.opencost_url:
            raise OpenCostNotConfiguredError(
                f"OpenCost is not configured for cluster {cluster_id}"
            )

        client: OpenCostClient = await self.factory.opencost(cluster)
        try:
            raw_items = await client.list_allocations(window, aggregate, step)
        except OpenCostInternalError as exc:
            raise OpenCostUnavailableError(f"OpenCost upstream error: {exc}") from exc
        except httpx.HTTPStatusError as exc:
            raise OpenCostUnavailableError(
                f"OpenCost returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            err_type = type(exc).__name__
            err_msg = str(exc) or repr(exc)
            logger.warning(
                "OpenCost HTTP error: %s: %s", err_type, err_msg, exc_info=True
            )
            raise OpenCostUnavailableError(
                f"OpenCost transport error ({err_type}): {err_msg}"
            ) from exc

        normalized = [self._normalize(item) for item in raw_items]
        normalized.sort(key=lambda a: a.total_cost, reverse=True)

        breakdown = self._sum_breakdown(normalized)
        coverage = self._coverage_from_window(normalized, window)

        return AllocationsTotalsResponse(
            cluster_id=str(cluster_id),
            period=coverage,
            breakdown=breakdown,
            cpu_efficiency=self._weighted_efficiency(normalized, "cpu"),
            ram_efficiency=self._weighted_efficiency(normalized, "ram"),
            generated_at=datetime.now(timezone.utc),
        )
