from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship   # ← добавлен relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cluster import ClusterProfile


UNALLOCATED = "_unallocated_"


class CostSnapshot(Base):
    __tablename__ = "cost_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id",
            "bucket_date",
            "namespace",
            "controller",
            "pod",
            "node",
            name="uq_cost_snapshots_alloc_day",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cluster_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False)

    namespace: Mapped[str] = mapped_column(Text, nullable=False, default=UNALLOCATED)
    controller: Mapped[str] = mapped_column(Text, nullable=False, default=UNALLOCATED)
    controller_kind: Mapped[str] = mapped_column(Text, nullable=False, default=UNALLOCATED)
    pod: Mapped[str] = mapped_column(Text, nullable=False, default=UNALLOCATED)
    node: Mapped[str] = mapped_column(Text, nullable=False, default=UNALLOCATED)

    minutes: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    cpu_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    ram_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    gpu_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    pv_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    network_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    load_balancer_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    shared_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    external_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))
    total_cost: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=Decimal(0))

    cpu_efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)
    ram_efficiency: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Absolute usage/request quantities (added in migration 0007) ──────
    # Stored alongside the ratio-based cpu_efficiency/ram_efficiency for
    # use by the recommendation engine. Bytes — not gibibytes — to avoid
    # precision loss; conversion to human units happens in the API layer.
    #
    # Semantics:
    #   *_requested = average requested resource during the bucket
    #   *_used      = average actual usage during the bucket
    #   *_hours     = integral of (resource * hours alive) over the bucket;
    #                 useful for unit-cost computation: cost / hours.
    #
    # All NOT NULL DEFAULT 0. Rows older than migration 0007 carry zeros —
    # the engine treats requested == 0 as "no data, skip".

    cpu_cores_requested: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal(0)
    )
    ram_bytes_requested: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal(0)
    )
    cpu_cores_used: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal(0)
    )
    ram_bytes_used: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), nullable=False, default=Decimal(0)
    )
    cpu_core_hours: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=Decimal(0)
    )
    ram_byte_hours: Mapped[Decimal] = mapped_column(
        Numeric(28, 0), nullable=False, default=Decimal(0)
    )

    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # ── Reverse relationship ─────────────────────────────────────────────
    # ClusterProfile declares: cost_snapshots = relationship(back_populates="cluster",
    # cascade="all, delete-orphan"). We mirror it here. lazy="raise" forbids implicit
    # lazy-load in async contexts — callers must use selectinload() if they need it.
    cluster: Mapped["ClusterProfile"] = relationship(
        "ClusterProfile",
        back_populates="cost_snapshots",
        lazy="raise",
    )
