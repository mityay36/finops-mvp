import asyncio
import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClusterProfile
from app.services.clients import OpenCostClient, VMClient

logger = logging.getLogger(__name__)


class ServiceFactory:
    """Per-cluster cache of HTTP clients with shared lifecycle.

    Clients are created lazily on first access and reused for the lifetime of the
    application. They are closed together via aclose_all() invoked from FastAPI
    lifespan shutdown.

    Cache invalidation: call invalidate(cluster_id) when a cluster's URLs change
    or when the cluster is deleted.
    """

    def __init__(self) -> None:
        self._opencost: dict[UUID, OpenCostClient] = {}
        self._vm: dict[UUID, VMClient] = {}
        self._lock = asyncio.Lock()

    async def opencost(self, cluster: ClusterProfile) -> OpenCostClient:
        async with self._lock:
            cached = self._opencost.get(cluster.id)
            if cached is not None and cached.base_url.rstrip("/") == cluster.opencost_url.rstrip("/"):
                return cached
            if cached is not None:
                # URL changed — close stale client first.
                await cached.aclose()
            client = OpenCostClient(cluster.opencost_url)
            self._opencost[cluster.id] = client
            return client

    async def vm(self, cluster: ClusterProfile) -> VMClient:
        async with self._lock:
            cached = self._vm.get(cluster.id)
            if cached is not None and cached.base_url.rstrip("/") == cluster.vm_url.rstrip("/"):
                return cached
            if cached is not None:
                await cached.aclose()
            client = VMClient(cluster.vm_url)
            self._vm[cluster.id] = client
            return client

    async def invalidate(self, cluster_id: UUID) -> None:
        """Drop and close any cached clients for a specific cluster."""
        async with self._lock:
            for cache in (self._opencost, self._vm):
                client = cache.pop(cluster_id, None)
                if client is not None:
                    await client.aclose()

    async def aclose_all(self) -> None:
        async with self._lock:
            tasks = []
            for cache in (self._opencost, self._vm):
                for client in cache.values():
                    tasks.append(client.aclose())
                cache.clear()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("ServiceFactory: all upstream HTTP clients closed (%d)", len(tasks))


# Singleton instance — initialized at import time, lifecycle owned by FastAPI lifespan.
service_factory = ServiceFactory()


def get_service_factory() -> ServiceFactory:
    """FastAPI dependency that returns the global ServiceFactory."""
    return service_factory


async def session_resolved_cluster(
    session: AsyncSession,
    cluster_id: UUID,
) -> ClusterProfile:
    """Helper: load cluster by id or raise. Used by routers/services that don't
    want to import ClusterService just to fetch one row."""
    cluster = await session.get(ClusterProfile, cluster_id)
    if cluster is None:
        raise LookupError(f"Cluster {cluster_id} not found")
    return cluster
