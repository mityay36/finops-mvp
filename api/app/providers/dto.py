from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class BillingRecordDTO:
    """Normalized billing record produced by a provider's ETL stream.

    All providers must yield records in this exact shape regardless of the
    underlying source format (CSV from S3, REST API, etc.).
    """

    period_start: datetime
    period_end: datetime
    service_name: str
    resource_id: str | None
    resource_name: str | None
    sku_name: str
    cost: Decimal
    currency: str
    label_namespace: str | None
    label_service: str | None
    is_preemptible: bool

    # Raw provider-native data preserved for forensics. Kept as plain dict.
    raw: dict[str, str] | None = None
