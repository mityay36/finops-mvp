import re
import logging
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.clients import OpenCostClient, OpenCostInternalError
from app.schemas.allocations import (
    Allocation,
    AllocationEfficiency,
    AllocationResources,
    AllocationsResponse,
)
from app.services.cluster_service import ClusterService
from app.services.factory import ServiceFactory

logger = logging.getLogger(__name__)

_WINDOW_PATTERN = re.compile(
    r"^(\d+[hdwm]"  # 7d, 24h, 4w, 1m
    r"|today|yesterday|week|month|lastweek|lastmonth"
    r"|\d{4}-\d{2}-\d{2}T[\d:.]+Z?,\d{4}-\d{2}-\d{2}T[\d:.]+Z?)$"
)
_STEP_PATTERN = re.compile(r"^\d+[hdwm]$")
_AGGREGATE_VALID = {"namespace", "controller", "pod", "node", "cluster", "label"}


class AllocationsValidationError(Exception):
    pass


class OpenCostNotConfiguredError(Exception):
    pass


class OpenCostUnavailableError(Exception):
    pass


class AllocationsService:
    def __init__(
        self,
        session: AsyncSession,
        service_factory: ServiceFactory,
    ) -> None:
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
        # OpenCost returns ISO-like strings, e.g. "2026-05-08T00:00:00Z"
        return datetime.fromisoformat(value.replace("Z", "+00:00"))

    @staticmethod
    def _to_decimal(value) -> Decimal:
        if value is None:
            return Decimal(0)
        try:
            return Decimal(str(value))
        except (ValueError, ArithmeticError):
            return Decimal(0)

    @classmethod
    def _normalize(cls, raw: dict) -> Allocation:
        props = raw.get("properties") or {}
        window = raw.get("window") or {}

        resources = AllocationResources(
            cpu_cost=cls._to_decimal(raw.get("cpuCost")),
            ram_cost=cls._to_decimal(raw.get("ramCost")),
            gpu_cost=cls._to_decimal(raw.get("gpuCost")),
            pv_cost=cls._to_decimal(raw.get("pvCost")),
            network_cost=cls._to_decimal(raw.get("networkCost")),
            load_balancer_cost=cls._to_decimal(raw.get("loadBalancerCost")),
            shared_cost=cls._to_decimal(raw.get("sharedCost")),
            external_cost=cls._to_decimal(raw.get("externalCost")),
        )
        total = (
            resources.cpu_cost
            + resources.ram_cost
            + resources.gpu_cost
            + resources.pv_cost
            + resources.network_cost
            + resources.load_balancer_cost
            + resources.shared_cost
            + resources.external_cost
        )

        efficiency = AllocationEfficiency(
            cpu_efficiency=raw.get("cpuEfficiency"),
            ram_efficiency=raw.get("ramEfficiency"),
        )

        return Allocation(
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
            total_cost=total,
            resources=resources,
            efficiency=efficiency,
        )

    async def list_allocations(
        self,
        cluster_id: UUID,
        window: str,
        aggregate: str,
        step: str | None,
        limit: int,
    ) -> AllocationsResponse:
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
                f"OpenCost returned HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.HTTPError as exc:
            err_type = type(exc).__name__
            err_msg = str(exc) or repr(exc)
            logger.warning("OpenCost HTTP error: %s: %s", err_type, err_msg, exc_info=True)
            raise OpenCostUnavailableError(
                f"OpenCost transport error ({err_type}): {err_msg}"
            ) from exc


        normalized = [self._normalize(item) for item in raw_items]
        normalized.sort(key=lambda a: a.total_cost, reverse=True)
        truncated = normalized[:limit]
        total_cost = sum((a.total_cost for a in normalized), Decimal(0))

        return AllocationsResponse(
            cluster_id=cluster_id,
            window=window,
            aggregate=aggregate,
            step=step,
            currency="USD",  # OpenCost returns USD by default; configurable in 6.x
            items=truncated,
            total_cost=total_cost,
        )
