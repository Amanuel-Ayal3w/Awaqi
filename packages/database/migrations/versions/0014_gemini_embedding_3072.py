"""No-op: 0013_gemini_embedding_dim already sets vector(1536) with hnsw index.

This revision is kept to preserve migration chain integrity for any environments
that previously ran an experimental 3072-dim migration.  On a fresh install the
upgrade is a no-op; on a legacy 3072-dim install it resets the column to 1536-d
(matching GEMINI_EMBEDDING_DIMENSION default) so indexes can be created.

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

TARGET_DIM = 1536


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
    return int(row[0]) - 4 if int(row[0]) > 4 else int(row[0])


def upgrade() -> None:
    if _embedding_dim() == TARGET_DIM:
        return
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(TARGET_DIM), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    pass
