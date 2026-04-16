from fastapi import APIRouter, Query
from app.services.victoria_metrics import vm
from app.services.opencost import opencost
from app.services.yc_billing import yc_billing

router = APIRouter()

# Пороги для rightsizing
CPU_RIGHTSIZING_THRESHOLD = 0.30   # использует < 30% от requests
RAM_RIGHTSIZING_THRESHOLD = 0.30
NODE_UTILIZATION_THRESHOLD = 0.40  # нода загружена < 40%

# Системные namespace — не трогаем
SYSTEM_NAMESPACES = {"kube-system", "kube-public", "kube-node-lease"}

# Экономию от перехода на preemptible в YC оцениваем как 80%
PREEMPTIBLE_SAVING_RATIO = 0.80


@router.get("/recommendations")
async def get_recommendations(window: str = Query("24h")):
    # Получаем данные из всех источников параллельно
    import asyncio
    allocs, cpu_ratios, ram_ratios, node_utils, vpa_recs = await asyncio.gather(
        opencost.get_allocations(window="30d"),
        vm.get_cpu_rightsizing(),
        vm.get_ram_rightsizing(),
        vm.get_node_utilization(),
        vm.get_vpa_recommendations(),
    )

    results = []

    # 1. RIGHTSIZING CPU
    cpu_ratio_map = {r["namespace"]: r["cpu_ratio"] for r in cpu_ratios}
    for ns, ratio in cpu_ratio_map.items():
        if ns in SYSTEM_NAMESPACES:
            continue
        if ratio < CPU_RIGHTSIZING_THRESHOLD:
            cost = allocs.get(ns, {}).get("totalCost", 0)
            overcost = cost * (1 - ratio)
            saving = round(overcost * 0.7, 2)  # консервативно 70% от overcost
            pct = round((1 - ratio) * 100)
            results.append({
                "type": "rightsizing_cpu",
                "resource": ns,
                "description": (
                    f"Namespace '{ns}' использует {round(ratio * 100)}% CPU от запрошенного. "
                    f"Рекомендуется уменьшить requests на {pct}%"
                ),
                "current_ratio": ratio,
                "potential_saving": saving,
                "risk": "low" if ratio < 0.10 else "medium",
                "action": "reduce_cpu_requests",
            })

    # 2. RIGHTSIZING RAM
    ram_ratio_map = {r["namespace"]: r["ram_ratio"] for r in ram_ratios}
    for ns, ratio in ram_ratio_map.items():
        if ns in SYSTEM_NAMESPACES:
            continue
        if ratio < RAM_RIGHTSIZING_THRESHOLD:
            cost = allocs.get(ns, {}).get("totalCost", 0)
            saving = round(cost * (1 - ratio) * 0.6, 2)
            pct = round((1 - ratio) * 100)
            results.append({
                "type": "rightsizing_ram",
                "resource": ns,
                "description": (
                    f"Namespace '{ns}' использует {round(ratio * 100)}% RAM от запрошенного. "
                    f"Рекомендуется уменьшить memory requests на {pct}%"
                ),
                "current_ratio": ratio,
                "potential_saving": saving,
                "risk": "low" if ratio < 0.10 else "medium",
                "action": "reduce_ram_requests",
            })

    # 3. SPOT / PREEMPTIBLE НОДЫ
    # Берём стоимость нод из YC Billing и рекомендуем preemptible
    billing = yc_billing.get_actual_costs(days=30)
    node_cost = billing.get("total", 0)
    already_preemptible = billing.get("has_preemptible_nodes", False)

    low_util_nodes = [n for n in node_utils if n["cpu_utilization"] < NODE_UTILIZATION_THRESHOLD]

    if low_util_nodes and not already_preemptible:
        # Ноды on-demand -> рекомендуем преобразовать в preemptible
        saving = round(node_cost * PREEMPTIBLE_SAVING_RATIO * 0.5, 2)
        results.append({
            "type": "spot_migration",
            "resource": "node-group/k8s-workers",
            "description": (
                f"Worker ноды загружены < {NODE_UTILIZATION_THRESHOLD*100:.0f}% CPU. "
                f"Перевод на preemptible ноды YC даст экономию ~80%"
            ),
            "potential_saving": saving,
            "risk": "medium",
            "action": "convert_to_preemptible",
            "notes": "Требует настройки PodDisruptionBudget и graceful termination",
        })
    elif already_preemptible and low_util_nodes:
        # Ноды уже preemptible — рекомендуем уменьшить размер node group
        results.append({
            "type": "node_downsize",
            "resource": "node-group/k8s-workers",
            "description": (
                f"Ноды уже preemptible, но загружены < {NODE_UTILIZATION_THRESHOLD*100:.0f}% CPU. "
                f"Рассмотрите уменьшение RAM/CPU профиля нод или сокращение их количества"
            ),
            "potential_saving": round(node_cost * 0.2, 2),  # 20% от уменьшения профиля
            "risk": "medium",
            "action": "resize_node_group",
            "notes": "Проверьте пиковую нагрузку перед изменением",
        })

    # 4. VPA RIGHTSIZING (если VPA задеплоен)
    for rec in vpa_recs[:5]:
        results.append({
            "type": "vpa_rightsizing",
            "resource": f"{rec['namespace']}/{rec['pod']}",
            "description": f"VPA рекомендует {rec['recommended_cpu']} CPU для {rec['pod']}",
            "potential_saving": None,
            "risk": "low",
            "action": "apply_vpa_recommendation",
            "recommended_value": rec["recommended_cpu"],
        })

    # Сортировка: по убыванию экономии
    results.sort(key=lambda x: -(x.get("potential_saving") or 0))

    total_savings = sum(r.get("potential_saving") or 0 for r in results)

    return {
        "window": window,
        "count": len(results),
        "estimated_monthly_saving": round(total_savings, 2),
        "items": results,
    }