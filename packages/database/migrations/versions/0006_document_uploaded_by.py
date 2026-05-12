"""Link documents to uploading admin user (optional FK to ba_user).

Revision ID: 0006_document_uploaded_by
Revises: 0005_phase_a_ingestion
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_document_uploaded_by"
down_revision: str | None = "0005_phase_a_ingestion"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ba_user.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_documents_uploaded_by_id",
        "documents",
        ["uploaded_by_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_uploaded_by_id", table_name="documents")
    op.drop_column("documents", "uploaded_by_id")
