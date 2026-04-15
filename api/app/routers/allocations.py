from fastapi import APIRouter, Query
from app.services.opencost import opencost

router = APIRouter()

@router.get("/allocations")
async def get_allocations(
    window: str = Query("30d", description="e.g. 24h, 7d, 30d"),
    aggregate: str = Query("namespace", description="namespace | label:team | pod"),
):
    data = await opencost.get_allocations(window=window, aggregate=aggregate)
    return {
        "window": window,
        "aggregate": aggregate,
        "count": len(data),
        "items": [
            {
                "name": k,
                "cpu_cost": round(v.get("cpuCost", 0), 4),
                "ram_cost": round(v.get("ramCost", 0), 4),
                "pv_cost": round(v.get("pvCost", 0), 4),
                "network_cost": round(v.get("networkCost", 0), 4),
                "total_cost": round(v.get("totalCost", 0), 4),
            }
            for k, v in sorted(data.items(), key=lambda x: x[1].get("totalCost", 0), reverse=True)
        ],
    }

@router.get("/allocations/team/{team}")
async def get_team_costs(team: str, window: str = Query("30d")):
    data = await opencost.get_allocations_by_label("team", window=window)
    item = data.get(team, {})
    return {
        "team": team,
        "window": window,
        "cpu_cost": round(item.get("cpuCost", 0), 4),
        "ram_cost": round(item.get("ramCost", 0), 4),
        "total_cost": round(item.get("totalCost", 0), 4),
    }

@router.get("/summary")
async def get_summary(window: str = Query("30d")):
    return await opencost.get_summary(window=window)
