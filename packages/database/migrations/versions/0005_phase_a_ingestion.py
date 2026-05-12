"""Phase A ingestion: document fields, chunk FTS, status enum values.

Revision ID: 0005_phase_a_ingestion
Revises: 0004_data_quality_constraints
Create Date: 2026-05-12
"""

import sqlalchemy as sa
from alembic import op

revision: str = "0005_phase_a_ingestion"
down_revision: str | None = "0004_data_quality_constraints"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # New document_status enum values (Postgres: add one at a time in DO blocks)
    op.execute(
        """
        DO $$ BEGIN
            ALTER TYPE document_status ADD VALUE 'processing';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            ALTER TYPE document_status ADD VALUE 'requires_manual_review';
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.add_column(
        "documents",
        sa.Column("byte_size", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "processing_stage",
            sa.String(32),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column("ingest_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("registry_key", sa.String(128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("proclamation_number", sa.String(128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("article_number", sa.String(128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column("effective_date", sa.Date(), nullable=True),
    )
    op.create_index(
        "ix_documents_registry_key",
        "documents",
        ["registry_key"],
        unique=True,
        postgresql_where=sa.text("registry_key IS NOT NULL"),
    )

    # Generated tsvector for PostgreSQL FTS (AWA-15)
    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN content_tsv tsvector
        GENERATED ALWAYS AS (to_tsvector('simple', coalesce(content, ''))) STORED;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_document_chunks_content_tsv
        ON document_chunks USING gin (content_tsv);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_content_tsv")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS content_tsv")

    op.drop_index("ix_documents_registry_key", table_name="documents")
    op.drop_column("documents", "effective_date")
    op.drop_column("documents", "article_number")
    op.drop_column("documents", "proclamation_number")
    op.drop_column("documents", "registry_key")
    op.drop_column("documents", "ingest_error")
    op.drop_column("documents", "processing_stage")
    op.drop_column("documents", "byte_size")

    # Cannot safely remove enum values in PostgreSQL without recreating type;
    # leave new enum values in place on downgrade.
