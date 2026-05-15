from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProviderCredential


class CredentialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_cluster(self, cluster_id: UUID) -> list[ProviderCredential]:
        stmt = (
            select(ProviderCredential)
            .where(ProviderCredential.cluster_id == cluster_id)
            .order_by(ProviderCredential.key_name)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def replace_all(
        self,
        cluster_id: UUID,
        encrypted_values: dict[str, str],
    ) -> list[ProviderCredential]:
        """Drop all existing credentials for the cluster and insert the new set."""
        await self.session.execute(
            delete(ProviderCredential).where(ProviderCredential.cluster_id == cluster_id)
        )
        items = [
            ProviderCredential(
                cluster_id=cluster_id,
                key_name=key,
                encrypted_value=value,
            )
            for key, value in encrypted_values.items()
        ]
        self.session.add_all(items)
        await self.session.flush()
        return items
