import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import ClusterProfile, ProviderType
from app.services.billing_sync_service import (
    BillingSyncBusyError,
    BillingSyncError,
    BillingSyncService,
)

logger = logging.getLogger(__name__)


async def sync_all_active_yc_clusters() -> None:
    """APScheduler entrypoint: iterate over all active YC clusters and trigger
    billing sync for each. Runs sequentially to avoid hammering S3 and DB.

    Each cluster is reserved + executed in independent sessions so a failure
    on one cluster does not abort the rest.
    """
    logger.info("Scheduled billing sync: starting")

    cluster_ids: list = []
    async with AsyncSessionLocal() as session:
        stmt = (
            select(ClusterProfile.id)
            .where(ClusterProfile.is_active.is_(True))
            .where(ClusterProfile.provider_type == ProviderType.YC)
        )
        cluster_ids = list((await session.execute(stmt)).scalars().all())

    if not cluster_ids:
        logger.info("Scheduled billing sync: no active YC clusters")
        return

    for cluster_id in cluster_ids:
        try:
            async with AsyncSessionLocal() as session:
                service = BillingSyncService(session)
                cluster = await session.get(ClusterProfile, cluster_id)
                if cluster is None:
                    continue
                run = await service.reserve_run(cluster, force_full=False)
                await session.commit()
                run_id = run.id
            # Execute outside the reservation session to avoid holding it open.
            await BillingSyncService.execute_run(run_id, cluster_id)
        except BillingSyncBusyError:
            logger.info("Scheduled billing sync: cluster %s busy, skipping", cluster_id)
        except BillingSyncError as exc:
            logger.warning(
                "Scheduled billing sync: cluster %s skipped: %s", cluster_id, exc
            )
        except Exception:  # noqa: BLE001
            logger.exception("Scheduled billing sync: cluster %s crashed", cluster_id)

    logger.info("Scheduled billing sync: finished")
