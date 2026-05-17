"""Run the recommendation engine for a single cluster and commit results.

Usage:
    python -m scripts.run_engine <cluster_id>

Writes/updates rows in `recommendations` table per engine output.
"""

from __future__ import annotations

import asyncio
import sys
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.services.recommendations.factory import build_engine


async def main(cluster_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        engine = build_engine(session)
        report = await engine.evaluate_cluster(cluster_id)
        await session.commit()

    print(f"cluster_id          = {report.cluster_id}")
    print(f"skipped_reason      = {report.skipped_reason}")
    print(f"valid_days          = {report.valid_days}")
    print(f"cluster_monthly_cost= ${report.cluster_monthly_cost:.4f}")
    print(f"cpu $/core-hour     = {report.cpu_unit_cost_per_core_hour:.6f}")
    print(f"ram $/GiB-hour      = {report.ram_unit_cost_per_gib_hour:.8f}")
    print(f"rules executed      = {len(report.per_rule)}")
    print()
    for rule_id, rep in report.per_rule.items():
        print(f"  rule={rule_id}")
        print(f"    findings_count = {rep.findings_count}")
        print(f"    upserted       = {rep.upserted}")
        print(f"    auto_resolved  = {rep.auto_resolved}")
        if rep.error:
            print(f"    error          = {rep.error}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m scripts.run_engine <cluster_id>", file=sys.stderr)
        sys.exit(2)
    asyncio.run(main(UUID(sys.argv[1])))