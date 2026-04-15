from fastapi import APIRouter, Query
from app.services.victoria_metrics import vm
from app.services.opencost import opencost

router = APIRouter()

RISK_THRESHOLDS = {
    "low": 0.10,      # <10% savings
    "medium": 0.30,   # 10-30% savings
    "high": 0.30,     # >30% savings
}

@router.get("/recommendations")
async def get_recommendations(window: str = Query("24h")):
    allocs = await opencost.get_allocations(window=window)
    idle = await vm.get_idle_namespaces(threshold=0.001)
    vpa_recs = await vm.get_vpa_recommendations()

    idle_ns = {r["namespace"] for r in idle}
    results = []

    # Idle namespace recommendations
    for item in idle:
        ns = item["namespace"]
        cost = allocs.get(ns, {}).get("totalCost", 0)
        results.append({
            "type": "idle_namespace",
            "resource": ns,
            "description": f"Namespace '{ns}' has avg CPU {item['avg_cpu']:.6f} cores — consider scaling to zero",
            "potential_saving": round(cost, 4),
            "risk": "low",
            "action": "scale_to_zero",
        })

    # Rightsizing от VPA
    for rec in vpa_recs[:10]:
        results.append({
            "type": "rightsizing",
            "resource": f"{rec['namespace']}/{rec['pod']}",
            "description": f"VPA recommends {rec['recommended_cpu']} CPU for {rec['pod']}",
            "potential_saving": None,
            "risk": "medium",
            "action": "update_requests",
            "recommended_value": rec["recommended_cpu"],
        })

    # Сортируем: сначала с известной экономией, потом по риску
    risk_order = {"low": 0, "medium": 1, "high": 2}
    results.sort(key=lambda x: (
        -(x.get("potential_saving") or 0),
        risk_order.get(x["risk"], 9)
    ))

    total_savings = sum(r.get("potential_saving") or 0 for r in results)

    return {
        "window": window,
        "count": len(results),
        "estimated_monthly_saving": round(total_savings, 2),
        "items": results,
    }
