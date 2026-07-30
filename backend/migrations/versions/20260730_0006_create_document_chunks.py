"""Create document chunks.

Revision ID: 20260730_0006
Revises: 20260730_0005
Create Date: 2026-07-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260730_0006"
down_revision: str | None = "20260730_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("char_start", sa.Integer(), nullable=False),
        sa.Column("char_end", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name=op.f("ck_document_chunks_chunk_index_not_negative"),
        ),
        sa.CheckConstraint(
            "page_number > 0",
            name=op.f("ck_document_chunks_page_number_positive"),
        ),
        sa.CheckConstraint(
            "char_start >= 0",
            name=op.f("ck_document_chunks_char_start_not_negative"),
        ),
        sa.CheckConstraint(
            "char_end > char_start",
            name=op.f("ck_document_chunks_char_range_valid"),
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) > 0",
            name=op.f("ck_document_chunks_content_not_blank"),
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "document_id"],
            ["documents.organization_id", "documents.id"],
            name="fk_document_chunks_organization_document",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "version_id"],
            ["document_versions.organization_id", "document_versions.id"],
            name="fk_document_chunks_organization_version",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name=op.f("fk_document_chunks_organization_id_organizations"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint(
            "organization_id",
            "version_id",
            "chunk_index",
            name="uq_document_chunks_organization_version_index",
        ),
    )
    op.create_index(
        op.f("ix_document_chunks_document_id"),
        "document_chunks",
        ["document_id"],
    )
    op.create_index(
        op.f("ix_document_chunks_organization_id"),
        "document_chunks",
        ["organization_id"],
    )
    op.create_index(
        op.f("ix_document_chunks_version_id"),
        "document_chunks",
        ["version_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_document_chunks_version_id"), table_name="document_chunks")
    op.drop_index(
        op.f("ix_document_chunks_organization_id"),
        table_name="document_chunks",
    )
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
