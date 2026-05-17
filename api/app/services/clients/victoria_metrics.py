from datetime import datetime
from typing import Any

from app.services.clients.base import BaseHTTPClient, ClientError


class VMClient(BaseHTTPClient):
    """Thin async client for VictoriaMetrics PromQL endpoints."""

    async def query(
        self, promql: str, *, time: datetime | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"query": promql}
        if time is not None:
            params["time"] = int(time.timestamp())
        payload = await self._get_json("api/v1/query", params=params)
        return self._extract_result(payload)

    async def query_range(
        self,
        promql: str,
        *,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> list[dict[str, Any]]:
        params = {
            "query": promql,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "step": step,
        }
        payload = await self._get_json("api/v1/query_range", params=params)
        return self._extract_result(payload)

    async def healthcheck(self) -> bool:
        try:
            await self.query("vm_app_uptime_seconds")
            return True
        except ClientError:
            return False

    @staticmethod
    def _extract_result(payload: dict[str, Any]) -> list[dict[str, Any]]:
        if payload.get("status") != "success":
            raise ClientError(f"VM query failed: {payload}")
        result = payload.get("data", {}).get("result", [])
        if not isinstance(result, list):
            raise ClientError("VM query returned invalid result shape")
        return result
