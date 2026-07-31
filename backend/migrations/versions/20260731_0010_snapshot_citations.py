"""Snapshot citations so reindexing preserves evidence.

Revision ID: 20260731_0010
Revises: 20260731_0009
Create Date: 2026-07-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260731_0010"
down_revision: str | None = "20260731_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = (
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("document_number", sa.BigInteger(), nullable=True),
        sa.Column("document_title", sa.String(length=240), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
    )
    for column in columns:
        op.add_column("message_citations", column)
    op.execute(
        """
        UPDATE message_citations AS citation
        SET document_id = chunk.document_id,
            version_id = chunk.version_id,
            document_number = document.document_number,
            document_title = document.title,
            page_number = chunk.page_number,
            content = chunk.content
        FROM document_chunks AS chunk
        JOIN documents AS document
          ON document.organization_id = chunk.organization_id
         AND document.id = chunk.document_id
        WHERE citation.organization_id = chunk.organization_id
          AND citation.chunk_id = chunk.id
        """
    )
    for column_name in (
        "document_id",
        "version_id",
        "document_number",
        "document_title",
        "page_number",
        "content",
    ):
        op.alter_column("message_citations", column_name, nullable=False)
    op.drop_constraint(
        "fk_message_citations_organization_id_document_chunks",
        "message_citations",
        type_="foreignkey",
    )
    op.alter_column("message_citations", "chunk_id", nullable=True)
    op.create_foreign_key(
        "fk_message_citations_chunk_id_document_chunks",
        "message_citations",
        "document_chunks",
        ["chunk_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.execute("DELETE FROM message_citations WHERE chunk_id IS NULL")
    op.drop_constraint(
        "fk_message_citations_chunk_id_document_chunks",
        "message_citations",
        type_="foreignkey",
    )
    op.alter_column("message_citations", "chunk_id", nullable=False)
    op.create_foreign_key(
        "fk_message_citations_organization_id_document_chunks",
        "message_citations",
        "document_chunks",
        ["organization_id", "chunk_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    for column_name in (
        "content",
        "page_number",
        "document_title",
        "document_number",
        "version_id",
        "document_id",
    ):
        op.drop_column("message_citations", column_name)
