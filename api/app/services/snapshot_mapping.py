"""OpenCost allocation JSON → cost_snapshots row mapping.

Stateless. Pure functions. No DB, no IO.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.snapshot import UNALLOCATED


# Per-spec, OpenCost emits allocation names following these patterns depending
# on the `aggregate` query param. We split safely without raising on edge cases.
def _split_pod_name(raw: str) -> tuple[str, str]:
    """For aggregate=pod, name is 'namespace/podname'."""
    if "/" in raw:
        ns, pod = raw.split("/", 1)
        return (ns or UNALLOCATED, pod or UNALLOCATED)
    return (UNALLOCATED, raw or UNALLOCATED)


def _safe_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal(0)
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return Decimal(0)


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (ValueError, TypeError):
        return None
    # OpenCost emits NaN/Inf for divisions by zero in efficiency calculations.
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f


def _bucket_date_from_window(alloc: dict[str, Any]) -> date | None:
    """Derive the day this allocation belongs to from its window.start.

    Falls back to None if the window field is missing or malformed — the caller
    should skip such rows rather than guess.
    """
    window = alloc.get("window") or {}
    start = window.get("start")
    if not start:
        return None
    try:
        # OpenCost returns RFC3339 with 'Z' suffix.
        if start.endswith("Z"):
            start = start[:-1] + "+00:00"
        dt = datetime.fromisoformat(start)
    except (ValueError, TypeError):
        return None
    return dt.astimezone(timezone.utc).date()


def map_pod_allocation(
    alloc: dict[str, Any],
    *,
    cluster_id: UUID,
) -> dict[str, Any] | None:
    """Map a single OpenCost allocation (aggregate=pod) to a cost_snapshots row.

    Returns None if the row cannot be built (missing window, idle entry, etc.)
    so the caller filters it out without raising.
    """
    name = alloc.get("_name") or alloc.get("name") or ""
    if not name or name == "__idle__":
        return None

    bucket = _bucket_date_from_window(alloc)
    if bucket is None:
        return None

    namespace, pod = _split_pod_name(name)

    # OpenCost exposes properties for controller/node when aggregate=pod with
    # `disableAggregatedCostModel=false`. They sometimes appear at top level,
    # sometimes under "properties". Be defensive.
    props = alloc.get("properties") or {}
    controller = (
        props.get("controller")
        or alloc.get("controller")
        or UNALLOCATED
    )
    controller_kind = (
        props.get("controllerKind")
        or alloc.get("controllerKind")
        or UNALLOCATED
    )
    node = (
        props.get("node")
        or alloc.get("node")
        or UNALLOCATED
    )
    # Override namespace from properties if present — it's authoritative.
    namespace = props.get("namespace") or namespace or UNALLOCATED

    # Cost components — names from OpenCost JSON.
    cpu_cost = _safe_decimal(alloc.get("cpuCost"))
    ram_cost = _safe_decimal(alloc.get("ramCost"))
    gpu_cost = _safe_decimal(alloc.get("gpuCost"))
    pv_cost = _safe_decimal(alloc.get("pvCost"))
    network_cost = _safe_decimal(alloc.get("networkCost"))
    lb_cost = _safe_decimal(alloc.get("loadBalancerCost"))
    shared_cost = _safe_decimal(alloc.get("sharedCost"))
    external_cost = _safe_decimal(alloc.get("externalCost"))
    total_cost = _safe_decimal(alloc.get("totalCost"))

    return {
        "cluster_id": cluster_id,
        "bucket_date": bucket,
        "namespace": namespace or UNALLOCATED,
        "controller": controller or UNALLOCATED,
        "controller_kind": controller_kind or UNALLOCATED,
        "pod": pod or UNALLOCATED,
        "node": node or UNALLOCATED,
        "minutes": float(alloc.get("minutes") or 0.0),
        "cpu_cost": cpu_cost,
        "ram_cost": ram_cost,
        "gpu_cost": gpu_cost,
        "pv_cost": pv_cost,
        "network_cost": network_cost,
        "load_balancer_cost": lb_cost,
        "shared_cost": shared_cost,
        "external_cost": external_cost,
        "total_cost": total_cost,
        "cpu_efficiency": _safe_float(alloc.get("cpuEfficiency")),
        "ram_efficiency": _safe_float(alloc.get("ramEfficiency")),
    }
