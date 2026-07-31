"""Harden embedding provenance and reindex events.

Revision ID: 20260731_0009
Revises: 20260731_0008
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_0009"
down_revision: str | None = "20260731_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("embedding_provider", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "document_chunks",
        sa.Column("embedding_model", sa.String(length=128), nullable=True),
    )
    # Existing vectors predate provenance tracking and must not be mixed with a
    # known model. The persisted text remains available for safe reindexing.
    op.execute("UPDATE document_chunks SET embedding = NULL")
    op.create_check_constraint(
        "ck_document_chunks_embedding_metadata_consistent",
        "document_chunks",
        "(embedding IS NULL AND embedding_provider IS NULL AND embedding_model IS NULL) "
        "OR (embedding IS NOT NULL AND embedding_provider IS NOT NULL "
        "AND embedding_model IS NOT NULL)",
    )
    op.create_index(
        "ix_document_chunks_embedding_provenance",
        "document_chunks",
        ["organization_id", "embedding_provider", "embedding_model"],
    )
    op.drop_constraint(
        "uq_outbox_events_event_type_aggregate_id",
        "outbox_events",
        type_="unique",
    )


def downgrade() -> None:
    op.execute("DELETE FROM outbox_events WHERE event_type = 'document.reindex_requested'")
    op.create_unique_constraint(
        "uq_outbox_events_event_type_aggregate_id",
        "outbox_events",
        ["event_type", "aggregate_id"],
    )
    op.drop_index(
        "ix_document_chunks_embedding_provenance",
        table_name="document_chunks",
    )
    op.drop_constraint(
        "ck_document_chunks_embedding_metadata_consistent",
        "document_chunks",
        type_="check",
    )
    op.drop_column("document_chunks", "embedding_model")
    op.drop_column("document_chunks", "embedding_provider")
