"""Add data-quality constraints for messages and document chunks.

Revision ID: 0004_data_quality_constraints
Revises: 0003_cu_auth_tables
Create Date: 2026-03-10
"""

from alembic import op

# revision identifiers
revision: str = "0004_data_quality_constraints"
down_revision: str | None = "0003_cu_auth_tables"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    # Ensure existing rows do not violate the new constraints.
    op.execute(
        """
        DELETE FROM document_chunks d
        USING (
            SELECT ctid
            FROM (
                SELECT
                    ctid,
                    ROW_NUMBER() OVER (
                        PARTITION BY document_id, chunk_index
                        ORDER BY created_at ASC, id ASC
                    ) AS rn
                FROM document_chunks
            ) ranked
            WHERE ranked.rn > 1
        ) dupes
        WHERE d.ctid = dupes.ctid
        """
    )
    op.execute(
        """
        UPDATE messages
        SET confidence_score = NULL
        WHERE confidence_score IS NOT NULL
          AND (confidence_score < 0 OR confidence_score > 1)
        """
    )

    op.create_unique_constraint(
        "uq_document_chunks_document_chunk_index",
        "document_chunks",
        ["document_id", "chunk_index"],
    )
    op.create_check_constraint(
        "ck_messages_confidence_score_range",
        "messages",
        "(confidence_score IS NULL) OR (confidence_score >= 0 AND confidence_score <= 1)",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_messages_confidence_score_range",
        "messages",
        type_="check",
    )
    op.drop_constraint(
        "uq_document_chunks_document_chunk_index",
        "document_chunks",
        type_="unique",
    )
