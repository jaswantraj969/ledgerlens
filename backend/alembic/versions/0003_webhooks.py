"""webhooks: signing secret, event filter, delivery details

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("webhooks", sa.Column("secret", sa.Text(), nullable=False, server_default=""))
    op.add_column(
        "webhooks",
        sa.Column("events", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default="[]"),
    )  # fmt: skip
    op.add_column("webhooks", sa.Column("active", sa.Boolean(), nullable=False,
                                        server_default=sa.true()))  # fmt: skip
    op.add_column(
        "webhook_deliveries",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False,
                  server_default="{}"),
    )  # fmt: skip
    op.add_column("webhook_deliveries", sa.Column("response_status", sa.Integer(), nullable=True))
    op.add_column("webhook_deliveries", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "webhook_deliveries", sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    for column in ("delivered_at", "last_error", "response_status", "payload"):
        op.drop_column("webhook_deliveries", column)
    for column in ("active", "events", "secret"):
        op.drop_column("webhooks", column)
