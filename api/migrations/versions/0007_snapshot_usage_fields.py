"""extend cost_snapshots with absolute usage/request fields

Adds six columns to cost_snapshots that store absolute resource quantities
parallel to the existing ratio-based cpu_efficiency/ram_efficiency:

  cpu_cores_requested   - average requested CPU cores during the bucket
  ram_bytes_requested   - average requested RAM in bytes
  cpu_cores_used        - average actual CPU usage in cores
  ram_bytes_used        - average actual RAM usage in bytes
  cpu_core_hours        - integral: cores * hours alive over the bucket
  ram_byte_hours        - integral: bytes * hours alive over the bucket

These fields enable the recommendation engine (Stage 6) to compute physical
right-sizing deltas and per-core-hour unit costs without falling back to live
VictoriaMetrics queries at evaluation time.

All columns are NOT NULL with DEFAULT 0. Historical rows are backfilled with
zeros — the recommendation engine ignores rows where cpu_cores_requested = 0,
which is the correct behaviour: we cannot reconstruct these values for past
days, so recommendations only become meaningful 14 days after this migration.

Revision ID: 0007_snapshot_usage_fields
Revises: 0006_cost_snapshots_redesign
Create Date: 2026-05-16
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0007_snapshot_usage_fields"
down_revision = "0006_cost_snapshots_redesign"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add columns with server_default='0' so existing rows get zeros
    # without requiring a separate UPDATE statement. This is fast on
    # PostgreSQL 11+ — adding a column with a constant default is O(1)
    # because PG stores the default in pg_attribute and only materializes
    # it on UPDATE.
    op.add_column(
        "cost_snapshots",
        sa.Column(
            "cpu_cores_requested",
            sa.Numeric(18, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cost_snapshots",
        sa.Column(
            "ram_bytes_requested",
            sa.Numeric(18, 0),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cost_snapshots",
        sa.Column(
            "cpu_cores_used",
            sa.Numeric(18, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cost_snapshots",
        sa.Column(
            "ram_bytes_used",
            sa.Numeric(18, 0),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cost_snapshots",
        sa.Column(
            "cpu_core_hours",
            sa.Numeric(18, 6),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "cost_snapshots",
        sa.Column(
            "ram_byte_hours",
            sa.Numeric(28, 0),
            nullable=False,
            server_default="0",
        ),
    )

    # Drop server_defaults — future inserts must specify values explicitly.
    # The default was only there to backfill existing rows; keeping it would
    # mask bugs where the ETL forgets to populate these fields.
    for col in (
        "cpu_cores_requested",
        "ram_bytes_requested",
        "cpu_cores_used",
        "ram_bytes_used",
        "cpu_core_hours",
        "ram_byte_hours",
    ):
        op.alter_column("cost_snapshots", col, server_default=None)


def downgrade() -> None:
    for col in (
        "ram_byte_hours",
        "cpu_core_hours",
        "ram_bytes_used",
        "cpu_cores_used",
        "ram_bytes_requested",
        "cpu_cores_requested",
    ):
        op.drop_column("cost_snapshots", col)
