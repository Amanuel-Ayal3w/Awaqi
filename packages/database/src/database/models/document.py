"""
Document and DocumentChunk ORM models.

- Document: represents an ingested regulatory PDF from mor.gov.et
- DocumentChunk: token-sized chunk of text + pgvector embedding + FTS tsvector (DB-generated)
"""

import uuid
from datetime import date, datetime, timezone
from enum import Enum as PyEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base

if TYPE_CHECKING:
    from database.models.auth import BaUser


class DocumentStatus(str, PyEnum):
    """High-level ingestion lifecycle (see ARCHITECTURE.md §2.1)."""

    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"
    REQUIRES_MANUAL_REVIEW = "requires_manual_review"


class ProcessingStage(str, PyEnum):
    """Sub-stages while status is processing (admin UI / AWA-17)."""

    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"


class Document(Base):
    """A regulatory document sourced from mor.gov.et or manually uploaded."""

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # SHA-256 of the raw file bytes — used for deduplication
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Optional: hash of source_url + byte_size for scraper registry (AWA-7)
    registry_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="am")
    status: Mapped[str] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
    processing_stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ingest_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Citation-oriented fields (AWA-13); populated at ingest from title/scraper heuristics
    proclamation_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    article_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    uploaded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ba_user.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationship
    uploader: Mapped["BaUser | None"] = relationship(
        "BaUser",
        foreign_keys=[uploaded_by_id],
    )
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("file_hash", name="uq_documents_file_hash"),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r} status={self.status}>"


EMBEDDING_DIM = 1024


class DocumentChunk(Base):
    """
    A text chunk of a Document along with its dense embedding.

    Full-text search: PostgreSQL stores generated column ``content_tsv`` (see migration
    0005); it is not mapped here so inserts omit it and the server fills it.
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    # Extra metadata: page_number, section_title, citation fields (AWA-13)
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_document_chunks_embedding_ivfflat",
            "embedding",
            postgresql_using="ivfflat",
        ),
        Index(
            "ix_document_chunks_content_trgm",
            "content",
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_document_chunks_document_chunk_index",
        ),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
