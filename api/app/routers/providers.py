from fastapi import APIRouter

from app.providers import PROVIDERS
from app.schemas import ProviderCredentialFieldRead, ProviderRead

router = APIRouter()


@router.get("/providers", response_model=list[ProviderRead])
async def list_providers() -> list[ProviderRead]:
    """List supported provider types and their required credential fields."""
    out: list[ProviderRead] = []
    for provider_cls in PROVIDERS.values():
        info = provider_cls.info()
        out.append(
            ProviderRead(
                type=info.type,
                name=info.name,
                description=info.description,
                credentials=[
                    ProviderCredentialFieldRead(
                        name=f.name,
                        label=f.label,
                        is_secret=f.is_secret,
                        required=f.required,
                        help_text=f.help_text,
                        placeholder=f.placeholder,
                    )
                    for f in info.credentials
                ],
            )
        )
    return out
