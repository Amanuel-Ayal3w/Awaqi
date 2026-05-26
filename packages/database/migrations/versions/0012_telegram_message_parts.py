"""Allow multiple tracked parts per Telegram message (text + image + file).

Revision ID: 0012_telegram_parts
Revises: 0011_telegram_scraper
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_telegram_parts"
down_revision = "0011_telegram_scraper"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "telegram_messages",
        sa.Column("content_part", sa.String(length=32), nullable=True),
    )
    op.execute(
        "UPDATE telegram_messages SET content_part = COALESCE(message_type, 'main') "
        "WHERE content_part IS NULL"
    )
    op.alter_column("telegram_messages", "content_part", nullable=False)
    op.drop_constraint("uq_telegram_messages_channel_msg", "telegram_messages", type_="unique")
    op.create_unique_constraint(
        "uq_telegram_messages_channel_msg_part",
        "telegram_messages",
        ["channel_username", "message_id", "content_part"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_telegram_messages_channel_msg_part", "telegram_messages", type_="unique"
    )
    op.create_unique_constraint(
        "uq_telegram_messages_channel_msg",
        "telegram_messages",
        ["channel_username", "message_id"],
    )
    op.drop_column("telegram_messages", "content_part")
