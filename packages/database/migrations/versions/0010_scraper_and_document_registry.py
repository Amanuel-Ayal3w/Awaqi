"""Scraper runs/config and document registry fields for MoR API ingestion.

Revision ID: 0010_scraper_registry
Revises: 0009
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_scraper_registry"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("external_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "source_system",
            sa.String(length=32),
            nullable=False,
            server_default="upload",
        ),
    )
    op.add_column(
        "documents",
        sa.Column("storage_path", sa.String(length=512), nullable=True),
    )
    op.create_index("ix_documents_external_id", "documents", ["external_id"], unique=False)
    op.create_index(
        "uq_documents_source_external",
        "documents",
        ["source_system", "external_id"],
        unique=True,
        postgresql_where=sa.text(
            "external_id IS NOT NULL AND source_system IS NOT NULL"
        ),
    )

    op.create_table(
        "scraper_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stats", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_scraper_runs_started_at", "scraper_runs", ["started_at"])

    op.create_table(
        "scraper_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seed_urls", sa.Text(), nullable=False),
        sa.Column("scheduler_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("cron_hour", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cron_minute", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_links", sa.Integer(), nullable=False, server_default="30"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    _DEFAULT_SEEDS = (
        "https://www.mor.gov.et/custom-law-proclamation,"
        "https://www.mor.gov.et/domestic-law-regulation,"
        "https://www.mor.gov.et/domestic-law-directive,"
        "https://www.mor.gov.et/domestic-law-proclamation,"
        "https://www.mor.gov.et/custome-law-regulation,"
        "https://www.mor.gov.et/custome-law-directive"
    )
    op.execute(
        f"INSERT INTO scraper_config (id, seed_urls, scheduler_enabled, cron_hour, cron_minute, max_links) "
        f"VALUES (1, '{_DEFAULT_SEEDS}', true, 0, 0, 30)"
    )


def downgrade() -> None:
    op.drop_table("scraper_config")
    op.drop_index("ix_scraper_runs_started_at", table_name="scraper_runs")
    op.drop_table("scraper_runs")
    op.drop_index("uq_documents_source_external", table_name="documents")
    op.drop_index("ix_documents_external_id", table_name="documents")
    op.drop_column("documents", "storage_path")
    op.drop_column("documents", "source_system")
    op.drop_column("documents", "external_id")
