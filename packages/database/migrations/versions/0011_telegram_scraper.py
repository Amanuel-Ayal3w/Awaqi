"""Telegram channel scraper tables (@morwestaa and similar).

Revision ID: 0011_telegram_scraper
Revises: 0010_scraper_registry
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_telegram_scraper"
down_revision = "0010_scraper_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "telegram_scraper_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("scrape_since", sa.Date(), nullable=False),
        sa.Column("max_messages_per_run", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("cron_hour", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cron_minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.execute(
        "INSERT INTO telegram_scraper_config "
        "(id, channel_username, scrape_since, max_messages_per_run) "
        "VALUES (1, 'morwestaa', '2026-04-01', 200)"
    )

    op.create_table(
        "telegram_scrape_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_telegram_scrape_runs_started_at",
        "telegram_scrape_runs",
        ["started_at"],
    )

    op.create_table(
        "telegram_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel_username", sa.String(length=64), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("message_type", sa.String(length=32), nullable=False),
        sa.Column("text_preview", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=512), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
        sa.Column("telegram_url", sa.String(length=512), nullable=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "scrape_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("telegram_scrape_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("skip_reason", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "channel_username",
            "message_id",
            name="uq_telegram_messages_channel_msg",
        ),
    )
    op.create_index(
        "ix_telegram_messages_posted_at",
        "telegram_messages",
        ["posted_at"],
    )
    op.create_index(
        "ix_telegram_messages_document_id",
        "telegram_messages",
        ["document_id"],
    )


def downgrade() -> None:
    op.drop_table("telegram_messages")
    op.drop_index("ix_telegram_scrape_runs_started_at", table_name="telegram_scrape_runs")
    op.drop_table("telegram_scrape_runs")
    op.drop_table("telegram_scraper_config")
