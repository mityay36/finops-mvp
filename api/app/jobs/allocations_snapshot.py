"""APScheduler entrypoint for hourly allocations snapshots."""

import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import ClusterProfile, SnapshotRunTrigger
from app.services.allocations_snapshot_service import (
    AllocationsSnapshotBusyError,
    AllocationsSnapshotError,
    AllocationsSnapshotService,
)

logger = logging.getLogger(__name__)


async def snapshot_all_active_clusters() -> None:
    """Iterate all active clusters and trigger an incremental allocations snapshot.

    Runs sequentially. Each cluster uses independent sessions so a failure on
    one does not abort the rest. Backfill is NOT auto-triggered — it is
    operator-invoked via the dedicated endpoint.
    """
    logger.info("Scheduled allocations snapshot: starting")

    cluster_ids: list = []
    async with AsyncSessionLocal() as session:
        stmt = select(ClusterProfile.id).where(ClusterProfile.is_active.is_(True))
        cluster_ids = list((await session.execute(stmt)).scalars().all())

    if not cluster_ids:
        logger.info("Scheduled allocations snapshot: no active clusters")
        return

    for cluster_id in cluster_ids:
        try:
            async with AsyncSessionLocal() as session:
                cluster = await session.get(ClusterProfile, cluster_id)
                if cluster is None:
                    continue
                service = AllocationsSnapshotService(session)
                run = await service.reserve_run(
                    cluster, trigger=SnapshotRunTrigger.SCHEDULER
                )
                await session.commit()
                run_id = run.id
            await AllocationsSnapshotService.execute_run(run_id, cluster_id)
        except AllocationsSnapshotBusyError:
            logger.info(
                "Scheduled allocations snapshot: cluster %s busy, skipping",
                cluster_id,
            )
        except AllocationsSnapshotError as exc:
            logger.warning(
                "Scheduled allocations snapshot: cluster %s skipped: %s",
                cluster_id,
                exc,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Scheduled allocations snapshot: cluster %s crashed",
                cluster_id,
            )

    logger.info("Scheduled allocations snapshot: finished")
