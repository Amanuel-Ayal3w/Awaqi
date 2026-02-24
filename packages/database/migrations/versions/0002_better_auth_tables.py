"""Replace admin_users with Better Auth tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-24

Changes:
- Create ba_user (replaces admin_users, adds emailVerified / image / camelCase timestamps)
- Create ba_session, ba_account, ba_verification
- Update chat_sessions.user_id FK → ba_user.id
- Drop admin_users
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # ── 1. ba_user ────────────────────────────────────────────────────────────
    # Reuses the existing admin_role enum ('superadmin' | 'editor').
    # Standard Better Auth columns use camelCase; custom fields use snake_case.
    op.create_table(
        "ba_user",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("emailVerified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("image", sa.Text, nullable=True),
        # Awaqi-specific fields kept alongside Better Auth standard fields
        sa.Column(
            "role",
            sa.Enum("superadmin", "editor", name="admin_role", create_type=False),
            nullable=False,
            server_default="editor",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_ba_user_email", "ba_user", ["email"], unique=True)

    # ── 2. ba_session ─────────────────────────────────────────────────────────
    op.create_table(
        "ba_session",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "userId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ba_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token", sa.Text, nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ipAddress", sa.Text, nullable=True),
        sa.Column("userAgent", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_ba_session_token", "ba_session", ["token"], unique=True)
    op.create_index("ix_ba_session_userId", "ba_session", ["userId"])

    # ── 3. ba_account ─────────────────────────────────────────────────────────
    op.create_table(
        "ba_account",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column(
            "userId",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ba_user.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("accountId", sa.Text, nullable=False),
        sa.Column("providerId", sa.Text, nullable=False),
        # For email/password auth the bcrypt hash lives here, not on ba_user
        sa.Column("password", sa.Text, nullable=True),
        sa.Column("accessToken", sa.Text, nullable=True),
        sa.Column("refreshToken", sa.Text, nullable=True),
        sa.Column("idToken", sa.Text, nullable=True),
        sa.Column("accessTokenExpiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refreshTokenExpiresAt", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scope", sa.Text, nullable=True),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_ba_account_userId", "ba_account", ["userId"])

    # ── 4. ba_verification ────────────────────────────────────────────────────
    op.create_table(
        "ba_verification",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("identifier", sa.Text, nullable=False),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("expiresAt", sa.DateTime(timezone=True), nullable=False),
        sa.Column("createdAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updatedAt", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    # ── 5. Migrate chat_sessions FK: admin_users.id → ba_user.id ─────────────
    op.drop_constraint("chat_sessions_user_id_fkey", "chat_sessions", type_="foreignkey")
    op.create_foreign_key(
        "chat_sessions_user_id_fkey",
        "chat_sessions",
        "ba_user",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── 6. Drop admin_users (no production data) ──────────────────────────────
    op.drop_index("ix_admin_users_email", table_name="admin_users")
    op.drop_table("admin_users")


def downgrade() -> None:
    # Restore admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(128), nullable=False),
        sa.Column(
            "role",
            sa.Enum("superadmin", "editor", name="admin_role", create_type=False),
            nullable=False,
            server_default="editor",
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"])

    # Restore chat_sessions FK to admin_users
    op.drop_constraint("chat_sessions_user_id_fkey", "chat_sessions", type_="foreignkey")
    op.create_foreign_key(
        "chat_sessions_user_id_fkey",
        "chat_sessions",
        "admin_users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.drop_table("ba_verification")
    op.drop_table("ba_account")
    op.drop_index("ix_ba_session_token", table_name="ba_session")
    op.drop_index("ix_ba_session_userId", table_name="ba_session")
    op.drop_table("ba_session")
    op.drop_index("ix_ba_user_email", table_name="ba_user")
    op.drop_table("ba_user")
