"""Add cu_user_id FK to chat_sessions for guest-to-customer session claiming.

Revision ID: 0007_chat_session_cu_user_id
Revises: 0006_document_uploaded_by
Create Date: 2026-05-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_chat_session_cu_user_id"
down_revision: str | None = "0006_document_uploaded_by"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "chat_sessions",
        sa.Column(
            "cu_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index("ix_chat_sessions_cu_user_id", "chat_sessions", ["cu_user_id"])
    op.create_foreign_key(
        "fk_chat_sessions_cu_user_id",
        "chat_sessions",
        "cu_user",
        ["cu_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_sessions_cu_user_id", "chat_sessions", type_="foreignkey")
    op.drop_index("ix_chat_sessions_cu_user_id", table_name="chat_sessions")
    op.drop_column("chat_sessions", "cu_user_id")
