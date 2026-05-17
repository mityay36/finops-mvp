import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import ClusterProfile
from app.models.base import Base, TimestampMixin


class ProviderCredential(TimestampMixin, Base):
    __tablename__ = "provider_credentials"
    __table_args__ = (
        UniqueConstraint(
            "cluster_id", "key_name", name="uq_provider_credentials_cluster_key_name"
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
    key_name: Mapped[str] = mapped_column(String(128), nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)

    cluster: Mapped["ClusterProfile"] = relationship(back_populates="credentials")
