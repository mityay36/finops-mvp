import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cluster import ClusterProfile


class OnPremTCOConfig(Base):
    __tablename__ = "onprem_tco_config"
    __table_args__ = (
        UniqueConstraint("cluster_id", name="uq_onprem_tco_config_cluster_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cluster_profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hardware_cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    amortization_years: Mapped[int] = mapped_column(nullable=False)
    power_watts: Mapped[int] = mapped_column(nullable=False)
    electricity_tariff: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    colocation_monthly: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0, server_default="0"
    )
    node_count: Mapped[int] = mapped_column(nullable=False)
    cpu_cores_per_node: Mapped[int] = mapped_column(nullable=False)
    ram_gb_per_node: Mapped[int] = mapped_column(nullable=False)
    cpu_to_ram_cost_ratio: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("0.70"), server_default="0.70"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    cluster: Mapped["ClusterProfile"] = relationship(back_populates="tco_config")
