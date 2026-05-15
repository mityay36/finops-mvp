from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import cipher
from app.models import ClusterProfile, ProviderCredential
from app.providers import get_provider
from app.repositories import ClusterRepository, CredentialRepository
from app.schemas.cluster import ClusterCreate, ClusterUpdate
from app.services.factory import service_factory


class ClusterServiceError(Exception):
    """Raised on business-rule violations in cluster management."""


class ClusterAlreadyExistsError(ClusterServiceError):
    pass


class ClusterNotFoundError(ClusterServiceError):
    pass


class CredentialValidationError(ClusterServiceError):
    pass


class ClusterService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.clusters = ClusterRepository(session)
        self.credentials = CredentialRepository(session)

    async def list_clusters(
        self, *, limit: int, offset: int
    ) -> tuple[list[ClusterProfile], int]:
        return await self.clusters.list(limit=limit, offset=offset)

    async def get_cluster(self, cluster_id: UUID) -> ClusterProfile:
        cluster = await self.clusters.get(cluster_id)
        if cluster is None:
            raise ClusterNotFoundError(f"Cluster {cluster_id} not found")
        return cluster

    async def create_cluster(self, payload: ClusterCreate) -> ClusterProfile:
        existing = await self.clusters.get_by_name(payload.name)
        if existing is not None:
            raise ClusterAlreadyExistsError(
                f"Cluster with name '{payload.name}' already exists"
            )
        try:
            cluster = await self.clusters.create(
                name=payload.name,
                provider_type=payload.provider_type,
                opencost_url=str(payload.opencost_url),
                vm_url=str(payload.vm_url),
                is_active=payload.is_active,
            )
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ClusterAlreadyExistsError(str(exc)) from exc
        await self.session.refresh(cluster)
        return cluster

    async def update_cluster(
        self, cluster_id: UUID, payload: ClusterUpdate
    ) -> ClusterProfile:
        cluster = await self.get_cluster(cluster_id)
        fields: dict = {}
        if payload.name is not None:
            fields["name"] = payload.name
        if payload.opencost_url is not None:
            fields["opencost_url"] = str(payload.opencost_url)
        if payload.vm_url is not None:
            fields["vm_url"] = str(payload.vm_url)
        if payload.is_active is not None:
            fields["is_active"] = payload.is_active

        if not fields:
            return cluster

        urls_changed = "opencost_url" in fields or "vm_url" in fields

        try:
            cluster = await self.clusters.update(cluster, fields)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ClusterAlreadyExistsError(str(exc)) from exc
        await self.session.refresh(cluster)

        if urls_changed:
            await service_factory.invalidate(cluster_id)

        return cluster


    async def delete_cluster(self, cluster_id: UUID) -> None:
        cluster = await self.get_cluster(cluster_id)
        await self.clusters.delete(cluster)
        await self.session.commit()
        await service_factory.invalidate(cluster_id)

    # ── Credentials ──────────────────────────────────────────────────────

    async def list_credentials(self, cluster_id: UUID) -> list[ProviderCredential]:
        await self.get_cluster(cluster_id)
        return await self.credentials.list_for_cluster(cluster_id)

    async def upsert_credentials(
        self, cluster_id: UUID, values: dict[str, str]
    ) -> list[ProviderCredential]:
        cluster = await self.get_cluster(cluster_id)
        provider_cls = get_provider(cluster.provider_type)
        try:
            cleaned = provider_cls.validate_credentials(values)
        except ValueError as exc:
            raise CredentialValidationError(str(exc)) from exc

        encrypted = {key: cipher.encrypt(value) for key, value in cleaned.items()}
        items = await self.credentials.replace_all(cluster_id, encrypted)
        await self.session.commit()
        return items
