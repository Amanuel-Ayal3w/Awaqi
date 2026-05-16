"""Add Better Auth admin plugin columns to ba_user.

Better Auth's admin plugin requires banned, banReason, and banExpires
columns on the user table for user ban management.

Revision ID: 0009
Revises: 0008
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008_cu_user_telegram_chat_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ba_user", sa.Column("banned", sa.Boolean(), nullable=True))
    op.add_column("ba_user", sa.Column("banReason", sa.Text(), nullable=True))
    op.add_column("ba_user", sa.Column("banExpires", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("ba_user", "banExpires")
    op.drop_column("ba_user", "banReason")
    op.drop_column("ba_user", "banned")
