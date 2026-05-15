from pydantic import BaseModel, Field


class CredentialUpsert(BaseModel):
    """Submit a complete set of credentials for a cluster. Replaces existing values."""

    values: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of credential field name -> plaintext value.",
    )


class CredentialMaskedRead(BaseModel):
    key_name: str
    has_value: bool = True
    masked_preview: str = Field(
        default="••••••••",
        description="Decorative placeholder. Real values are never returned via API.",
    )
