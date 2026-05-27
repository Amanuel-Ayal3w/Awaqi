"""Resize pgvector embeddings for Gemini (1536-dim). Existing E5 vectors must be re-indexed.

Uses gemini-embedding-001 with output_dimensionality=1536 — half the native
3072-d output, still excellent RAG quality, and within pgvector's 2000-d index
limit for all pgvector versions.  Switches index type from ivfflat to hnsw
(better recall at high dims).

Revision ID: 0013_gemini_embedding_dim
Revises: 0012_telegram_parts
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0013_gemini_embedding_dim"
down_revision = "0012_telegram_parts"
branch_labels = None
depends_on = None

NEW_DIM = 1536


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(NEW_DIM), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(1024), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
