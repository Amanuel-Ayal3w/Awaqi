"""Merge embedding dim branch heads into a single head.

Unifies the 0013_embedding_dim_1536 branch (revision "0013") and the
0013_gemini_embedding_dim -> 0014_gemini_embedding_3072 branch so that
``alembic upgrade head`` is unambiguous on all environments.

Revision ID: cfc06938f5b2
Revises: 0013, 0014_gemini_embedding_3072
"""

from alembic import op

revision: str = "cfc06938f5b2"
down_revision: tuple[str, str] = ("0013", "0014_gemini_embedding_3072")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
