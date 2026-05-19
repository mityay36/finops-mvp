"""Engine factory: assembles all registered rules.

Edit this file to add/remove rules — engine itself is rule-agnostic.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.recommendations.engine import RecommendationEngineService
from app.services.recommendations.types import RuleEvaluator
from app.services.recommendations.rules.rightsizing_cpu import RightsizingCpuRule
from app.services.recommendations.rules.oom_risk_ram import OomRiskRamRule
from app.services.recommendations.rules.idle_workload import IdleWorkloadRule


def build_engine(
    session: AsyncSession,
    *,
    window_days: int = 14,
    min_valid_days: int = 10,
) -> RecommendationEngineService:
    rules: list[RuleEvaluator] = [
        RightsizingCpuRule(),
        OomRiskRamRule(),
        IdleWorkloadRule(),
    ]
    return RecommendationEngineService(
        session,
        rules=rules,
        window_days=window_days,
        min_valid_days=min_valid_days,
    )
