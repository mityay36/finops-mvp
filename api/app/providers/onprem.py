from app.models.cluster import ProviderType
from app.providers.base import BaseProvider


class OnPremProvider(BaseProvider):
    PROVIDER_TYPE = ProviderType.ONPREM
    DISPLAY_NAME = "On-Prem Cluster"
    DESCRIPTION = (
        "Self-hosted Kubernetes cluster. Costs are derived from TCO config (hardware, power, "
        "colocation), not from a cloud billing source."
    )
    REQUIRED_CREDENTIALS = []  # No external credentials needed; TCO config lives in onprem_tco_config.
