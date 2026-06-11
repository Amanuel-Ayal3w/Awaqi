"""Add notification_config and notification_logs tables.

Revision ID: 0016_notification_tables
Revises: 0015_gemini_embedding_dim_3072
"""

import sqlalchemy as sa
from alembic import op

revision = "0016_notification_tables"
down_revision = "0015_gemini_embedding_dim_3072"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("interval_hours", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("email_recipients", sa.Text(), nullable=False, server_default=""),
        sa.Column("sms_recipients", sa.Text(), nullable=False, server_default=""),
        sa.Column("min_relevance_score", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "notification_logs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "doc_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("doc_title", sa.String(512), nullable=True),
        sa.Column("channel", sa.String(8), nullable=False),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(512), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="sent"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("trigger", sa.String(16), nullable=False, server_default="scheduled"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_notification_logs_doc_id",
        "notification_logs",
        ["doc_id"],
    )
    op.create_index(
        "ix_notification_logs_created_at",
        "notification_logs",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_notification_logs_created_at", table_name="notification_logs")
    op.drop_index("ix_notification_logs_doc_id", table_name="notification_logs")
    op.drop_table("notification_logs")
    op.drop_table("notification_config")
