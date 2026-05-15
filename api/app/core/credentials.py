import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import CryptoError, cipher
from app.models import ProviderCredential

logger = logging.getLogger(__name__)


class CredentialsResolverError(Exception):
    """Raised when credentials cannot be resolved or decrypted."""


async def resolve_credentials(
    session: AsyncSession,
    cluster_id: UUID,
) -> dict[str, str]:
    """Load all credentials for a cluster and return them as plaintext key->value map."""
    stmt = select(ProviderCredential).where(ProviderCredential.cluster_id == cluster_id)
    rows = (await session.execute(stmt)).scalars().all()

    out: dict[str, str] = {}
    for row in rows:
        try:
            out[row.key_name] = cipher.decrypt(row.encrypted_value)
        except CryptoError as exc:
            logger.error(
                "Failed to decrypt credential %s for cluster %s: %s",
                row.key_name,
                cluster_id,
                exc,
            )
            raise CredentialsResolverError(
                f"Failed to decrypt credential '{row.key_name}' for cluster {cluster_id}. "
                "FERNET_KEY may have changed since this value was stored."
            ) from exc
    return out
