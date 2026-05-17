import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.sync_run import BillingSyncRun
from app.models.tco import OnPremTCOConfig
from app.models.snapshot import CostSnapshot
from app.models.billing import BillingRecord
from app.models.base import Base, TimestampMixin
from app.models import ProviderCredential



if TYPE_CHECKING:
    from app.models.recommendation import Recommendation

class ProviderType(str, enum.Enum):
    YC = "yc"
    ONPREM = "onprem"


class ClusterProfile(TimestampMixin, Base):
    __tablename__ = "cluster_profiles"
    __table_args__ = (
        UniqueConstraint("name", name="uq_cluster_profiles_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provider_type: Mapped[ProviderType] = mapped_column(
        Enum(
            ProviderType,
            name="provider_type_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    opencost_url: Mapped[str] = mapped_column(String(512), nullable=False)
    vm_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    credentials: Mapped[list["ProviderCredential"]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    billing_records: Mapped[list["BillingRecord"]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    cost_snapshots: Mapped[list["CostSnapshot"]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    recommendations: Mapped[list["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="cluster",
        cascade="all, delete-orphan",
        lazy="raise",
    )
    tco_config: Mapped["OnPremTCOConfig | None"] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    sync_runs: Mapped[list["BillingSyncRun"]] = relationship(
        back_populates="cluster",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
