"""
Document and DocumentChunk ORM models.

- Document: represents an ingested regulatory PDF from mor.gov.et
- DocumentChunk: a 1024-token chunk of text + its pgvector embedding
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.base import Base


class DocumentStatus(str, PyEnum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


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
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="am")
    status: Mapped[str] = mapped_column(
        Enum(DocumentStatus, name="document_status"),
        nullable=False,
        default=DocumentStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("file_hash", name="uq_documents_file_hash"),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r} status={self.status}>"


# pgvector dimension matches multilingual-e5-large output
EMBEDDING_DIM = 1024


class DocumentChunk(Base):
    """
    A fixed-size text chunk of a Document along with its dense embedding.

    Chunking strategy: 1024 tokens, 100-token overlap.
    Embedding model: multilingual-e5-large → 1024-dimensional vectors.
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
    # 1024-dimensional dense vector from multilingual-e5-large
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=True)
    # Extra metadata: page_number, section_title, etc.
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationship
    document: Mapped["Document"] = relationship("Document", back_populates="chunks")

    __table_args__ = (
        # Approximate Nearest Neighbour index (IVFFlat, cosine similarity)
        # Created AFTER initial data load for best performance:
        #   CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
        Index("ix_document_chunks_embedding_ivfflat", "embedding", postgresql_using="ivfflat"),
        # GIN index for fast PostgreSQL full-text search on the content column
        Index("ix_document_chunks_content_fts", "content", postgresql_using="gin",
              postgresql_ops={"content": "gin_trgm_ops"}),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
