"""Merge 0017 migration heads.

Revision ID: 0018_merge_0017_heads
Revises: 0017_announcements, 0017_enforcement_status
"""

revision = "0018_merge_0017_heads"
down_revision = ("0017_announcements", "0017_enforcement_status")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
