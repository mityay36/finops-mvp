"""recommendations table with partial unique index on open rows

Stores rule engine output. Lifecycle:
  open ──► closed_resolved   (engine: rule no longer triggers)
       ──► applied           (user marked as applied)
       ──► dismissed         (user dismissed with reason)

Natural key for ACTIVE recommendations:
  (cluster_id, rule_id, target_namespace, target_controller) WHERE status='open'

Closed rows (applied/dismissed/closed_resolved) accumulate as history.
A new 'open' for the same target+rule can coexist with previously-closed
rows of the same key — the partial unique index permits this.

Revision ID: 0008_recommendations
Revises: 0007_snapshot_usage_fields
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "0008_recommendations"
down_revision = "0007_snapshot_usage_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "cluster_id",
            UUID(as_uuid=True),
            sa.ForeignKey("cluster_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("target_kind", sa.Text(), nullable=False),
        sa.Column("target_namespace", sa.Text(), nullable=False),
        sa.Column("target_controller", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("severity", sa.Text(), nullable=False, server_default="info"),
        sa.Column(
            "monthly_saving_usd",
            sa.Numeric(18, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "evidence",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('open','applied','dismissed','closed_resolved')",
            name="ck_recommendations_status",
        ),
        sa.CheckConstraint(
            "severity IN ('info','warning','critical')",
            name="ck_recommendations_severity",
        ),
        sa.CheckConstraint(
            "monthly_saving_usd >= 0",
            name="ck_recommendations_saving_nonneg",
        ),
    )

    # Partial unique: only one OPEN recommendation per (cluster, rule, ns, ctrl).
    # Closed rows can pile up as history.
    op.create_index(
        "uq_recommendations_open",
        "recommendations",
        ["cluster_id", "rule_id", "target_namespace", "target_controller"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )

    # Read-API path: list by cluster filtered by status.
    op.create_index(
        "ix_recommendations_cluster_status",
        "recommendations",
        ["cluster_id", "status"],
    )

    # For per-rule queries (engine internal: "find all open rows from rule X").
    op.create_index(
        "ix_recommendations_cluster_rule_status",
        "recommendations",
        ["cluster_id", "rule_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_recommendations_cluster_rule_status", table_name="recommendations")
    op.drop_index("ix_recommendations_cluster_status", table_name="recommendations")
    op.drop_index("uq_recommendations_open", table_name="recommendations")
    op.drop_table("recommendations")