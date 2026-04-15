import httpx
from app.config import settings

class VictoriaMetricsService:
    def __init__(self):
        self.base_url = settings.vm_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def query(self, promql: str) -> list:
        resp = await self.client.get(
            f"{self.base_url}/api/v1/query",
            params={"query": promql},
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("result", [])

    async def query_range(self, promql: str, start: str, end: str, step: str = "1h") -> list:
        resp = await self.client.get(
            f"{self.base_url}/api/v1/query_range",
            params={"query": promql, "start": start, "end": end, "step": step},
        )
        resp.raise_for_status()
        return resp.json().get("data", {}).get("result", [])

    async def get_idle_namespaces(self, threshold: float = 0.01) -> list[dict]:
        """Namespace с avg CPU < threshold за последние 24h"""
        results = await self.query(
            f'avg by(namespace) (rate(container_cpu_usage_seconds_total{{namespace!=""}}[24h])) < {threshold}'
        )
        return [
            {
                "namespace": r["metric"].get("namespace", "unknown"),
                "avg_cpu": round(float(r["value"][1]), 6),
            }
            for r in results
        ]

    async def get_vpa_recommendations(self) -> list[dict]:
        """VPA рекомендации — только recommend mode"""
        results = await self.query(
            'kube_verticalpodautoscaler_status_recommendation_containerrecommendations_target'
            '{resource="cpu"}'
        )
        recs = []
        for r in results:
            m = r["metric"]
            recs.append({
                "namespace": m.get("namespace"),
                "pod": m.get("container"),
                "resource": m.get("resource"),
                "recommended_cpu": round(float(r["value"][1]), 4),
            })
        return recs

vm = VictoriaMetricsService()
