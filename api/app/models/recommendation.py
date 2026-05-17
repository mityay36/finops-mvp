from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.cluster import ClusterProfile


# ── Enums (Text-backed, NOT native PG enum) ──────────────────────────────
# Text + StrEnum keeps migrations cheap when we add a new value later;
# a native PG enum would require ALTER TYPE ADD VALUE in a separate
# transaction, complicating Alembic.

class RecommendationStatus(StrEnum):
    OPEN = "open"
    APPLIED = "applied"
    DISMISSED = "dismissed"
    CLOSED_RESOLVED = "closed_resolved"


class RecommendationSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class RecommendationTargetKind(StrEnum):
    CONTROLLER = "controller"
    NAMESPACE = "namespace"
    NODE = "node"


# Rule IDs are also string constants — keep them centralized to avoid typos
# leaking into evidence JSON or natural keys.
class RuleId(StrEnum):
    RIGHTSIZING_CPU = "rightsizing_cpu"
    OOM_RISK_RAM = "oom_risk_ram"
    IDLE_WORKLOAD = "idle_workload"


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open','applied','dismissed','closed_resolved')",
            name="ck_recommendations_status",
        ),
        CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_recommendations_severity",
        ),
        CheckConstraint(
            "monthly_saving_usd >= 0",
            name="ck_recommendations_saving_nonneg",
        ),
        # Indexes are declared in the migration; we don't redeclare them
        # here to avoid metadata drift if we later evolve their definitions
        # (especially the partial unique).
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    cluster_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cluster_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    rule_id: Mapped[str] = mapped_column(Text, nullable=False)
    target_kind: Mapped[str] = mapped_column(Text, nullable=False)
    target_namespace: Mapped[str] = mapped_column(Text, nullable=False)
    target_controller: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=RecommendationStatus.OPEN.value
    )
    severity: Mapped[str] = mapped_column(
        Text, nullable=False, default=RecommendationSeverity.INFO.value
    )

    monthly_saving_usd: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), nullable=False, default=Decimal(0)
    )
    evidence: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    cluster: Mapped["ClusterProfile"] = relationship(
        "ClusterProfile",
        back_populates="recommendations",
        lazy="raise",
    )
