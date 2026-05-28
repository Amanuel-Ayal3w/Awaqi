"""Add enforcement_status column to documents table.

Revision ID: 0017_enforcement_status
Revises: 0016_notification_tables
"""

import sqlalchemy as sa
from alembic import op

revision = "0017_enforcement_status"
down_revision = "0016_notification_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE enforcement_status AS ENUM ('in_effect', 'draft')"
    )
    op.add_column(
        "documents",
        sa.Column(
            "enforcement_status",
            sa.Enum("in_effect", "draft", name="enforcement_status"),
            nullable=False,
            server_default="in_effect",
        ),
    )


def downgrade() -> None:
    op.drop_column("documents", "enforcement_status")
    op.execute("DROP TYPE IF EXISTS enforcement_status")
