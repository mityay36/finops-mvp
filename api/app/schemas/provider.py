from pydantic import BaseModel

from app.models.cluster import ProviderType


class ProviderCredentialFieldRead(BaseModel):
    name: str
    label: str
    is_secret: bool
    required: bool
    help_text: str | None = None
    placeholder: str | None = None


class ProviderRead(BaseModel):
    type: ProviderType
    name: str
    description: str
    credentials: list[ProviderCredentialFieldRead]
