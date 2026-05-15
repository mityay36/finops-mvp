from app.providers.base import BaseProvider, CredentialFieldSpec, ProviderInfo
from app.providers.onprem import OnPremProvider
from app.providers.yc import YCProvider
from app.models.cluster import ProviderType


PROVIDERS: dict[ProviderType, type[BaseProvider]] = {
    ProviderType.YC: YCProvider,
    ProviderType.ONPREM: OnPremProvider,
}


def get_provider(provider_type: ProviderType) -> type[BaseProvider]:
    try:
        return PROVIDERS[provider_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider type: {provider_type}") from exc


__all__ = [
    "BaseProvider",
    "CredentialFieldSpec",
    "ProviderInfo",
    "OnPremProvider",
    "YCProvider",
    "PROVIDERS",
    "get_provider",
]
