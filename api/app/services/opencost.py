import httpx
from app.config import settings

class OpenCostService:
    def __init__(self):
        self.base_url = settings.opencost_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_allocations(self, window: str = "30d", aggregate: str = "namespace") -> dict:
        resp = await self.client.get(
            f"{self.base_url}/allocation/compute",
            params={"window": window, "aggregate": aggregate, "accumulate": "true"},
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenCost возвращает list из одного dict
        if isinstance(data.get("data"), list) and data["data"]:
            return data["data"][0]
        return {}

    async def get_allocations_by_label(self, label: str, window: str = "30d") -> dict:
        resp = await self.client.get(
            f"{self.base_url}/allocation/compute",
            params={"window": window, "aggregate": f"label:{label}", "accumulate": "true"},
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data.get("data"), list) and data["data"]:
            return data["data"][0]
        return {}

    async def get_summary(self, window: str = "30d") -> dict:
        allocs = await self.get_allocations(window=window)
        total = sum(v.get("totalCost", 0) for v in allocs.values())
        top = sorted(allocs.items(), key=lambda x: x[1].get("totalCost", 0), reverse=True)[:5]
        return {
            "total_cost": round(total, 2),
            "namespace_count": len(allocs),
            "top_namespaces": [
                {"namespace": k, "cost": round(v.get("totalCost", 0), 2)} for k, v in top
            ],
        }

opencost = OpenCostService()
