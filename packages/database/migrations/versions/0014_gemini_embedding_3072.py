"""Resize pgvector embeddings to 3072 (if 0013 was applied at 1536). Re-index after upgrade.

Revision ID: 0014_gemini_embedding_3072
Revises: 0013_gemini_embedding_dim
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0014_gemini_embedding_3072"
down_revision = "0013_gemini_embedding_dim"
branch_labels = None
depends_on = None

NEW_DIM = 3072


def _embedding_dim() -> int | None:
    bind = op.get_bind()
    row = bind.execute(
        sa.text(
            """
            SELECT a.atttypmod
            FROM pg_attribute a
            JOIN pg_class c ON a.attrelid = c.oid
            WHERE c.relname = 'document_chunks'
              AND a.attname = 'embedding'
              AND NOT a.attisdropped
            """
        )
    ).first()
    if not row or row[0] is None:
        return None
    # pgvector typmod: dimension + 4 (header)
    return int(row[0]) - 4 if int(row[0]) > 4 else int(row[0])


def upgrade() -> None:
    current = _embedding_dim()
    if current == NEW_DIM:
        return
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
    current = _embedding_dim()
    if current == 1536:
        return
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_ivfflat "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
