"""
Customer auth ORM models — CuUser and CuSession.

These map to the cu_user and cu_session tables created in migration 0003.
They are completely separate from the BaUser/BaSession admin tables.
Better Auth uses camelCase column names by default; SQLAlchemy mapped_column
name= parameters handle the Python snake_case ↔ DB camelCase translation.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class CuUser(Base):
    """
    End-customer / chat user managed by the customer Better Auth instance.

    Deliberately has NO role or is_active fields — those are admin-only
    concepts. Customers are always active once registered.
    """

    __tablename__ = "cu_user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    email_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, name="emailVerified"
    )
    image: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="createdAt"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, name="updatedAt"
    )

    sessions: Mapped[list["CuSession"]] = relationship(
        "CuSession", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CuUser id={self.id} email={self.email!r}>"


class CuSession(Base):
    """
    Active customer Better Auth session — one row per logged-in browser tab/device.

    FastAPI's get_current_customer dependency queries this table (JOINed with CuUser)
    to validate incoming Bearer tokens.
    """

    __tablename__ = "cu_session"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cu_user.id", ondelete="CASCADE"),
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

    user: Mapped["CuUser"] = relationship("CuUser", back_populates="sessions")

    def __repr__(self) -> str:
        return f"<CuSession id={self.id!r} user={self.user_id} expires={self.expires_at}>"
