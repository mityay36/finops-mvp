"""redesign cost_snapshots for daily pod-level allocations + add allocations_snapshot_runs

Revision ID: 0006_cost_snapshots_redesign
Revises: 3790dea440f6
Create Date: 2026-05-15 20:35:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_cost_snapshots_redesign"
down_revision = "3790dea440f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("cost_snapshots")

    op.create_table(
        "cost_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cluster_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bucket_date", sa.Date(), nullable=False),
        sa.Column("namespace", sa.Text(), nullable=False, server_default="_unallocated_"),
        sa.Column("controller", sa.Text(), nullable=False, server_default="_unallocated_"),
        sa.Column("controller_kind", sa.Text(), nullable=False, server_default="_unallocated_"),
        sa.Column("pod", sa.Text(), nullable=False, server_default="_unallocated_"),
        sa.Column("node", sa.Text(), nullable=False, server_default="_unallocated_"),
        sa.Column("minutes", sa.Float(), nullable=False, server_default="0"),
        sa.Column("cpu_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("ram_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("gpu_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("pv_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("network_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("load_balancer_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("shared_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("external_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("total_cost", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("cpu_efficiency", sa.Float(), nullable=True),
        sa.Column("ram_efficiency", sa.Float(), nullable=True),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_unique_constraint(
        "uq_cost_snapshots_alloc_day",
        "cost_snapshots",
        ["cluster_id", "bucket_date", "namespace", "controller", "pod", "node"],
    )

    op.create_index(
        "ix_cost_snapshots_cluster_day",
        "cost_snapshots",
        ["cluster_id", "bucket_date"],
    )
    op.create_index(
        "ix_cost_snapshots_cluster_namespace_day",
        "cost_snapshots",
        ["cluster_id", "namespace", "bucket_date"],
    )

    op.create_table(
        "allocations_snapshot_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cluster_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("days_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rows_upserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_alloc_snapshot_runs_cluster_started",
        "allocations_snapshot_runs",
        ["cluster_id", sa.text("started_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_alloc_snapshot_runs_cluster_started")
    op.drop_table("allocations_snapshot_runs")
    op.drop_index("ix_cost_snapshots_cluster_namespace_day")
    op.drop_index("ix_cost_snapshots_cluster_day")
    op.drop_constraint("uq_cost_snapshots_alloc_day", "cost_snapshots")
    op.drop_table("cost_snapshots")

    op.create_table(
        "cost_snapshots",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "cluster_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cluster_profiles.id"),
            nullable=False,
        ),
        sa.Column("snapshot_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("namespace", sa.String(), nullable=True),
        sa.Column("cpu_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("ram_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("pv_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("network_cost", sa.Numeric(18, 6), nullable=True),
        sa.Column("total_cost", sa.Numeric(18, 6), nullable=True),
    )
