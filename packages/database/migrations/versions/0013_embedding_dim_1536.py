"""Resize document_chunks.embedding from vector(1024) to vector(1536).

Uses gemini-embedding-2 with output_dimensionality=1536 — half the native
3072-d output, still excellent quality, and within pgvector's 2000-d index
limit. Switches index type from ivfflat to hnsw (better recall at high dims).
All existing chunk rows must be re-indexed after this migration.

Revision ID: 0013
Revises: 0012_telegram_parts
"""

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012_telegram_parts"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")

    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(1536) "
        "USING NULL"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding "
        "ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")

    op.execute(
        "ALTER TABLE document_chunks "
        "ALTER COLUMN embedding TYPE vector(1024) "
        "USING NULL"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding "
        "ON document_chunks USING ivfflat (embedding vector_cosine_ops) "
        "WITH (lists = 100)"
    )
