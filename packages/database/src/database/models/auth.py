"""
Better Auth ORM models — BaUser and BaSession.

These map to the ba_user and ba_session tables created in migration 0002.
Better Auth uses camelCase column names by default; SQLAlchemy mapped_column
name= parameters handle the Python snake_case ↔ DB camelCase translation.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class AdminRole(str, PyEnum):
    SUPERADMIN = "superadmin"
    EDITOR = "editor"


class BaUser(Base):
    """
    Awaqi admin user managed by Better Auth.

    Standard Better Auth fields use camelCase DB columns.
    Custom fields (role, is_active) use snake_case DB columns.
    """

    __tablename__ = "ba_user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, name="emailVerified"
    )
    image: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Awaqi-specific custom fields (snake_case DB columns via Better Auth additionalFields)
    role: Mapped[str] = mapped_column(
        Enum(AdminRole, name="admin_role"),
        nullable=False,
        default=AdminRole.EDITOR,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="createdAt"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="updatedAt"
    )

    chat_sessions: Mapped[list["ChatSession"]] = relationship(  # noqa: F821
        "ChatSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<BaUser id={self.id} email={self.email!r} role={self.role}>"


class BaSession(Base):
    """
    Active Better Auth session — one row per logged-in browser tab/device.

    FastAPI's get_current_admin dependency queries this table (JOINed with BaUser)
    to validate incoming Bearer tokens without needing JWT or a shared secret.
    """

    __tablename__ = "ba_session"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        name="userId",
    )
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="expiresAt"
    )
    ip_address: Mapped[str | None] = mapped_column(Text, nullable=True, name="ipAddress")
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True, name="userAgent")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="createdAt"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="updatedAt"
    )

    user: Mapped["BaUser"] = relationship("BaUser")

    def __repr__(self) -> str:
        return f"<BaSession id={self.id!r} user={self.user_id} expires={self.expires_at}>"
