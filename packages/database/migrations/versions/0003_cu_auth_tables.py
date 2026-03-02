"""Add cu_user and cu_session tables for customer auth

Revision ID: 0003_cu_auth_tables
Revises: 0001_combined
Create Date: 2026-03-02
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0003_cu_auth_tables"
down_revision: str | None = "0001_combined"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── cu_user ───────────────────────────────────────────────────────────────
    # Mirror of ba_user but without admin-specific role / is_active fields.
    op.create_table(
        "cu_user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("emailVerified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("image", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cu_user_email", "cu_user", ["email"], unique=True)

    # ── cu_session ────────────────────────────────────────────────────────────
    op.create_table(
        "cu_session",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "userId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cu_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.Text, nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ipAddress", sa.Text, nullable=True),
        sa.Column("userAgent", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_cu_session_token", "cu_session", ["token"], unique=True)
    op.create_index("ix_cu_session_userId", "cu_session", ["userId"])

    # ── cu_account (Better Auth oauth credential store) ───────────────────────
    op.create_table(
        "cu_account",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "userId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cu_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
    op.create_index("ix_cu_account_userId", "cu_account", ["userId"])

    # ── cu_verification ───────────────────────────────────────────────────────
    op.create_table(
        "cu_verification",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("identifier", sa.Text, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("cu_verification")
    op.drop_index("ix_cu_account_userId", table_name="cu_account")
    op.drop_table("cu_account")
    op.drop_index("ix_cu_session_userId", table_name="cu_session")
    op.drop_index("ix_cu_session_token", table_name="cu_session")
    op.drop_table("cu_session")
    op.drop_index("ix_cu_user_email", table_name="cu_user")
    op.drop_table("cu_user")
