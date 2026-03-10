"""Initial combined schema with Better Auth and pgvector

Revision ID: 0001_combined
Revises: —
Create Date: 2026-03-02
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001_combined"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    # ── Extensions ──────────────────────────────────────────────────────────────
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    # ── documents ─────────────────────────────────────────────────────────────
    status_enum = sa.Enum("pending", "indexed", "failed", name="document_status")
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("language", sa.String(8), nullable=False, server_default="am"),
        sa.Column("status", status_enum, nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── document_chunks ───────────────────────────────────────────────────────
    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column("chunk_metadata", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])
    # GIN trigram index is safe inside a transaction
    op.execute(
        "CREATE INDEX ix_document_chunks_content_trgm "
        "ON document_chunks USING gin (content gin_trgm_ops)"
    )

    # ── Better Auth ───────────────────────────────────────────────────────────
    role_enum = sa.Enum("superadmin", "editor", name="admin_role")

    op.create_table(
        "ba_user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("emailVerified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("image", sa.Text, nullable=True),
        sa.Column("role", role_enum, nullable=False, server_default="editor"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ba_user_email", "ba_user", ["email"], unique=True)

    op.create_table(
        "ba_session",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("userId", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ba_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.Text, nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ipAddress", sa.Text, nullable=True),
        sa.Column("userAgent", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ba_session_token", "ba_session", ["token"], unique=True)
    op.create_index("ix_ba_session_userId", "ba_session", ["userId"])

    op.create_table(
        "ba_account",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("userId", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ba_user.id", ondelete="CASCADE"), nullable=False),
        sa.Column("accountId", sa.Text, nullable=False),
        sa.Column("providerId", sa.Text, nullable=False),
        sa.Column("password", sa.Text, nullable=True),
        sa.Column("accessToken", sa.Text, nullable=True),
        sa.Column("refreshToken", sa.Text, nullable=True),
        sa.Column("idToken", sa.Text, nullable=True),
        sa.Column("accessTokenExpiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refreshTokenExpiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_ba_account_userId", "ba_account", ["userId"])

    op.create_table(
        "ba_verification",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("identifier", sa.Text, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── chat_sessions ─────────────────────────────────────────────────────────
    channel_enum = sa.Enum("web", "telegram", name="channel")
    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("channel", channel_enum, nullable=False, server_default="web"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ba_user.id", ondelete="SET NULL"), nullable=True),
        sa.Column("language", sa.String(8), nullable=False, server_default="am"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])

    # ── messages ──────────────────────────────────────────────────────────────
    role_msg_enum = sa.Enum("user", "assistant", name="message_role")
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", role_msg_enum, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("cited_chunks", postgresql.JSONB, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])

    # ── feedback ──────────────────────────────────────────────────────────────
    feedback_enum = sa.Enum("thumbs_up", "thumbs_down", name="feedback_rating")
    op.create_table(
        "feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("rating", feedback_enum, nullable=False),
        sa.Column("comment", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_feedback_message_id", "feedback", ["message_id"])

    # ── IVFFlat ANN index ──────────────────────────────────────────────────────
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    ))


def downgrade() -> None:
    op.drop_index("ix_feedback_message_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_messages_session_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
    op.drop_table("ba_verification")
    op.drop_index("ix_ba_account_userId", table_name="ba_account")
    op.drop_table("ba_account")
    op.drop_index("ix_ba_session_userId", table_name="ba_session")
    op.drop_index("ix_ba_session_token", table_name="ba_session")
    op.drop_table("ba_session")
    op.drop_index("ix_ba_user_email", table_name="ba_user")
    op.drop_table("ba_user")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
    op.drop_table("documents")

    for enum_name in ["feedback_rating", "message_role", "channel", "admin_role", "document_status"]:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))