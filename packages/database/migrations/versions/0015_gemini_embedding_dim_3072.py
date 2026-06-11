"""Resize pgvector embeddings to Gemini native 3072 dimension.

Revision ID: 0015_gemini_embedding_dim_3072
Revises: cfc06938f5b2
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0015_gemini_embedding_dim_3072"
down_revision = "cfc06938f5b2"
branch_labels = None
depends_on = None

TARGET_DIM = 3072


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
<<<<<<< HEAD
    # pgvector hnsw/ivfflat indexes support at most 2000 dimensions for the plain
    # ``vector`` type. At 3072-d we index the half-precision ``halfvec`` projection
    # (indexable up to 4000 dims); the query path casts to halfvec to match.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw ((embedding::halfvec(3072)) halfvec_cosine_ops)"
    )
=======
    # pgvector ANN indexes on `vector` currently support up to 2000 dimensions.
    # Keep native Gemini 3072-d vectors, but skip ANN index creation.
>>>>>>> d13fe7308c7c83ea1636dd767c75872e6a858582


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_ivfflat")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS embedding")
    op.add_column(
        "document_chunks",
        sa.Column("embedding", Vector(1536), nullable=True),
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )
