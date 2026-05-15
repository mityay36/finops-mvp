from typing import Any
import httpx

from app.services.clients.base import BaseHTTPClient, ClientError

class OpenCostInternalError(Exception):
    """OpenCost responded with HTTP 200 but reported an internal error in body."""


class OpenCostClient(BaseHTTPClient):
    """Thin async client for OpenCost /allocation API."""

    async def get_allocations(
        self,
        *,
        window: str = "30d",
        aggregate: str = "namespace",
        accumulate: bool = True,
    ) -> dict[str, Any]:
        params = {
            "window": window,
            "aggregate": aggregate,
            "accumulate": str(accumulate).lower(),
        }
        payload = await self._get_json("allocation", params=params)
        data = payload.get("data") or []
        if not isinstance(data, list) or not data:
            return {}
        # OpenCost returns a list of result-buckets; with accumulate=true there is exactly one.
        first = data[0] if isinstance(data[0], dict) else {}
        # Filter out the synthetic "__idle__" entry unless explicitly requested by caller.
        return {k: v for k, v in first.items() if k != "__idle__"}

    async def get_summary(self, *, window: str = "30d") -> dict[str, float]:
        allocations = await self.get_allocations(window=window, aggregate="cluster")
        if not allocations:
            return {"cpu_cost": 0.0, "ram_cost": 0.0, "pv_cost": 0.0, "network_cost": 0.0, "total_cost": 0.0}
        # With aggregate=cluster there is typically one bucket.
        try:
            bucket = next(iter(allocations.values()))
        except StopIteration as exc:
            raise ClientError("Empty cluster aggregation from OpenCost") from exc
        return {
            "cpu_cost": float(bucket.get("cpuCost", 0.0)),
            "ram_cost": float(bucket.get("ramCost", 0.0)),
            "pv_cost": float(bucket.get("pvCost", 0.0)),
            "network_cost": float(bucket.get("networkCost", 0.0)),
            "total_cost": float(bucket.get("totalCost", 0.0)),
        }

    async def healthcheck(self) -> bool:
        """Cheap probe used by /clusters/{id}/diagnostics."""
        try:
            await self._get_json("allocation", params={"window": "1h", "aggregate": "cluster"})
            return True
        except ClientError:
            return False

    async def list_allocations(
        self,
        window: str,
        aggregate: str,
        step: str | None = None,
        *,
        timeout: float | httpx.Timeout | None = None,
    ) -> list[dict]:
        params = {
            "window": window,
            "aggregate": aggregate,
            "accumulate": "false" if step else "true",
        }
        if step:
            params["step"] = step

        request_kwargs: dict = {"params": params}
        if timeout is not None:
            request_kwargs["timeout"] = timeout

        resp = await self._client.get("/allocation", **request_kwargs)
        resp.raise_for_status()
        payload = resp.json() or {}

        inner_code = payload.get("code")
        if inner_code is not None and inner_code != 200:
            message = payload.get("message") or payload.get("error") or "no details"
            raise OpenCostInternalError(
                f"OpenCost responded with internal code {inner_code}: {message}"
            )

        raw_windows = payload.get("data")
        if not raw_windows:
            return []

        flattened: list[dict] = []
        for window_dict in raw_windows:
            if not isinstance(window_dict, dict):
                continue
            for alloc_name, alloc_data in window_dict.items():
                if alloc_name == "__idle__":
                    continue
                if not isinstance(alloc_data, dict):
                    continue
                alloc_data["_name"] = alloc_name
                flattened.append(alloc_data)
        return flattened
