import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


if TYPE_CHECKING:
    from app.models.cluster import ClusterProfile


class BillingRecord(Base):
    __tablename__ = "billing_records"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "period_start",
            "resource_id",
            "sku_name",
            name="uq_billing_records_cluster_period_resource_sku",
        ),
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
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    service_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True)
    resource_name: Mapped[str] = mapped_column(String(512), nullable=True)
    sku_name: Mapped[str] = mapped_column(String(255), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    currency: Mapped[str] = mapped_column(
        String(16), nullable=False, default="RUB", server_default="RUB"
    )
    label_namespace: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    label_service: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    is_preemptible: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    cluster: Mapped["ClusterProfile"] = relationship(back_populates="billing_records")
