"""
ChatSession, Message, and Feedback ORM models.

- ChatSession: a conversation thread (web or Telegram, guest or admin)
- Message:     a single turn in the conversation (user or assistant)
- Feedback:    thumbs-up / thumbs-down rating on an assistant message
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class Channel(str, PyEnum):
    WEB = "web"
    TELEGRAM = "telegram"


class MessageRole(str, PyEnum):
    USER = "user"
    ASSISTANT = "assistant"


class FeedbackRating(str, PyEnum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"


class ChatSession(Base):
    """
    Represents one multi-turn conversation thread.

    Guest sessions have user_id=None and are kept alive by Redis TTL.
    Admin sessions are persisted here permanently.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    channel: Mapped[str] = mapped_column(
        Enum(Channel, name="channel"),
        nullable=False,
        default=Channel.WEB,
    )
    # NULL → anonymous/guest session; non-NULL → authenticated admin (references ba_user)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ba_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="am")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["BaUser"] = relationship(  # noqa: F821
        "BaUser", back_populates="chat_sessions"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="session", cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<ChatSession id={self.id} channel={self.channel} user={self.user_id}>"


class Message(Base):
    """One turn in a ChatSession (either a user query or an assistant response)."""

    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        Enum(MessageRole, name="message_role"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # List of {chunk_id, score, excerpt} dicts serialised as JSONB
    cited_chunks: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    # RAG confidence score in [0, 1]; None for user messages
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    feedback: Mapped["Feedback | None"] = relationship(
        "Feedback", back_populates="message", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role} session={self.session_id}>"


class Feedback(Base):
    """User rating (thumbs up/down) on a single assistant Message."""

    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Each message can only receive one piece of feedback (unique FK)
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    rating: Mapped[str] = mapped_column(
        Enum(FeedbackRating, name="feedback_rating"),
        nullable=False,
    )
    comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    message: Mapped["Message"] = relationship("Message", back_populates="feedback")

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} message={self.message_id} rating={self.rating}>"
