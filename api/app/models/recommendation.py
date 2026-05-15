import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


class RecommendationType(str, enum.Enum):
    RIGHTSIZING_CPU = "rightsizing_cpu"
    RIGHTSIZING_RAM = "rightsizing_ram"
    SPOT_MIGRATION = "spot_migration"
    NODE_DOWNSIZE = "node_downsize"
    VPA_RIGHTSIZING = "vpa_rightsizing"
    IDLE_NAMESPACE = "idle_namespace"


class RecommendationRisk(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendationStatus(str, enum.Enum):
    NEW = "new"
    APPLIED = "applied"
    DISMISSED = "dismissed"


class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_recommendations_fingerprint"),
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
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    type: Mapped[RecommendationType] = mapped_column(
        Enum(
            RecommendationType,
            name="recommendation_type_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    resource: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    potential_saving: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    risk: Mapped[RecommendationRisk] = mapped_column(
        Enum(
            RecommendationRisk,
            name="recommendation_risk_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(
            RecommendationStatus,
            name="recommendation_status_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=RecommendationStatus.NEW,
        server_default=RecommendationStatus.NEW.value,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    cluster: Mapped["ClusterProfile"] = relationship(back_populates="recommendations")
