"""Add telegram_chat_id to cu_user for Telegram account linking.

Revision ID: 0008_cu_user_telegram_chat_id
Revises: 0007_chat_session_cu_user_id
Create Date: 2026-05-15
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0008_cu_user_telegram_chat_id"
down_revision: str | None = "0007_chat_session_cu_user_id"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "cu_user",
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_cu_user_telegram_chat_id", "cu_user", ["telegram_chat_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_cu_user_telegram_chat_id", table_name="cu_user")
    op.drop_column("cu_user", "telegram_chat_id")
