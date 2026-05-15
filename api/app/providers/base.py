from dataclasses import dataclass
from datetime import datetime

from app.models.cluster import ProviderType


@dataclass(frozen=True)
class CredentialFieldSpec:
    """Declarative description of a credential field. Frontend uses it to render form."""

    name: str
    label: str
    is_secret: bool = False
    required: bool = True
    help_text: str | None = None
    placeholder: str | None = None


@dataclass(frozen=True)
class ProviderInfo:
    """Public-facing metadata about a provider for the frontend."""

    type: ProviderType
    name: str
    description: str
    credentials: list[CredentialFieldSpec]


class BaseProvider:
    """Base class for cloud / on-prem provider integrations."""

    PROVIDER_TYPE: ProviderType
    DISPLAY_NAME: str
    DESCRIPTION: str = ""
    REQUIRED_CREDENTIALS: list[CredentialFieldSpec] = []

    @classmethod
    def info(cls) -> ProviderInfo:
        return ProviderInfo(
            type=cls.PROVIDER_TYPE,
            name=cls.DISPLAY_NAME,
            description=cls.DESCRIPTION,
            credentials=list(cls.REQUIRED_CREDENTIALS),
        )

    @classmethod
    def validate_credentials(cls, credentials: dict[str, str]) -> dict[str, str]:
        """Ensure submitted credentials match REQUIRED_CREDENTIALS spec.

        Returns the validated dict (only known keys, stripped values).
        Raises ValueError on missing required keys or unknown keys.
        """
        spec_by_name = {field.name: field for field in cls.REQUIRED_CREDENTIALS}
        unknown = set(credentials) - set(spec_by_name)
        if unknown:
            raise ValueError(f"Unknown credential fields: {sorted(unknown)}")

        cleaned: dict[str, str] = {}
        missing: list[str] = []
        for field in cls.REQUIRED_CREDENTIALS:
            value = credentials.get(field.name, "")
            if isinstance(value, str):
                value = value.strip()
            if not value:
                if field.required:
                    missing.append(field.name)
                continue
            cleaned[field.name] = value

        if missing:
            raise ValueError(f"Missing required credential fields: {sorted(missing)}")

        return cleaned

    # ── Billing ETL contract ─────────────────────────────────────────────

    async def iter_billing_records(  # noqa: D401
        self,
        credentials: dict[str, str],
        *,
        since: datetime,
        until: datetime,
    ):
        """Yield BillingRecordDTO objects for the given time window.

        Implementations should be async generators. Default implementation
        signals that the provider does not support billing ingestion (e.g. on-prem).
        """
        raise NotImplementedError(
            f"Provider {self.__class__.__name__} does not support billing ingestion"
        )
        # The yield below is unreachable but keeps mypy/Python aware that this
        # is the contract of an async generator for subclasses.
        if False:  # pragma: no cover
            yield  # type: ignore[unreachable]
