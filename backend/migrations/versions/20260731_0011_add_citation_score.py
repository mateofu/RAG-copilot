"""Persist citation retrieval score.

Revision ID: 20260731_0011
Revises: 20260731_0010
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0011"
down_revision: str | None = "20260731_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "message_citations",
        sa.Column("retrieval_score", sa.Float(), nullable=True),
    )
    op.execute("UPDATE message_citations SET retrieval_score = 0")
    op.alter_column("message_citations", "retrieval_score", nullable=False)


def downgrade() -> None:
    op.drop_column("message_citations", "retrieval_score")
