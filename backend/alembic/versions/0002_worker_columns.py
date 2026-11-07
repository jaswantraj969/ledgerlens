"""worker: job error detail, dead-letter time, degraded extraction runs

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("error_detail", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("dead_lettered_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("extraction_runs", sa.Column("degraded_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("extraction_runs", "degraded_reason")
    op.drop_column("jobs", "dead_lettered_at")
    op.drop_column("jobs", "error_detail")
