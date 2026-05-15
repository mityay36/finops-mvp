from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClusterProfile, ProviderType


class ClusterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list(self, limit: int, offset: int) -> tuple[list[ClusterProfile], int]:
        total_stmt = select(func.count()).select_from(ClusterProfile)
        total = (await self.session.execute(total_stmt)).scalar_one()

        stmt = (
            select(ClusterProfile)
            .order_by(ClusterProfile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all()), total

    async def get(self, cluster_id: UUID) -> ClusterProfile | None:
        return await self.session.get(ClusterProfile, cluster_id)

    async def get_by_name(self, name: str) -> ClusterProfile | None:
        stmt = select(ClusterProfile).where(ClusterProfile.name == name)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        provider_type: ProviderType,
        opencost_url: str,
        vm_url: str,
        is_active: bool,
    ) -> ClusterProfile:
        cluster = ClusterProfile(
            name=name,
            provider_type=provider_type,
            opencost_url=opencost_url,
            vm_url=vm_url,
            is_active=is_active,
        )
        self.session.add(cluster)
        await self.session.flush()
        return cluster

    async def update(self, cluster: ClusterProfile, fields: dict) -> ClusterProfile:
        for key, value in fields.items():
            setattr(cluster, key, value)
        await self.session.flush()
        return cluster

    async def delete(self, cluster: ClusterProfile) -> None:
        await self.session.delete(cluster)
        await self.session.flush()
