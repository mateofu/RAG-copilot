from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.modules.documents.domain.status import DocumentStatus


def enum_values[EnumType: StrEnum](enum_type: type[EnumType]) -> list[str]:
    return [member.value for member in enum_type]


class DocumentModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        CheckConstraint(
            "char_length(btrim(title)) BETWEEN 1 AND 240",
            name="title_not_blank",
        ),
        UniqueConstraint(
            "organization_id",
            "document_number",
            name="uq_documents_organization_id_document_number",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_documents_organization_id_id",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_number: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
    )


class DocumentVersionModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        CheckConstraint("version_number > 0", name="version_number_positive"),
        CheckConstraint("size_bytes > 0", name="size_bytes_positive"),
        CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'",
            name="sha256_format",
        ),
        CheckConstraint(
            "char_length(btrim(original_filename)) BETWEEN 1 AND 255",
            name="original_filename_not_blank",
        ),
        CheckConstraint(
            "char_length(btrim(storage_key)) BETWEEN 1 AND 1024",
            name="storage_key_not_blank",
        ),
        UniqueConstraint(
            "document_id",
            "version_number",
            name="uq_document_versions_document_id_version_number",
        ),
        UniqueConstraint(
            "organization_id",
            "sha256",
            name="uq_document_versions_organization_id_sha256",
        ),
        UniqueConstraint(
            "organization_id",
            "id",
            name="uq_document_versions_organization_id_id",
        ),
        ForeignKeyConstraint(
            ["organization_id", "document_id"],
            ["documents.organization_id", "documents.id"],
            name="fk_document_versions_organization_document",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(127), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(
            DocumentStatus,
            name="document_status",
            values_callable=enum_values,
        ),
        default=DocumentStatus.PENDING,
        server_default=DocumentStatus.PENDING.value,
        nullable=False,
    )
    failure_code: Mapped[str | None] = mapped_column(String(64))
    failure_message: Mapped[str | None] = mapped_column(String(500))


class DocumentChunkModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        CheckConstraint("chunk_index >= 0", name="chunk_index_not_negative"),
        CheckConstraint("page_number > 0", name="page_number_positive"),
        CheckConstraint("char_start >= 0", name="char_start_not_negative"),
        CheckConstraint("char_end > char_start", name="char_range_valid"),
        CheckConstraint("char_length(btrim(content)) > 0", name="content_not_blank"),
        UniqueConstraint(
            "organization_id",
            "version_id",
            "chunk_index",
            name="uq_document_chunks_organization_version_index",
        ),
        ForeignKeyConstraint(
            ["organization_id", "document_id"],
            ["documents.organization_id", "documents.id"],
            name="fk_document_chunks_organization_document",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["organization_id", "version_id"],
            ["document_versions.organization_id", "document_versions.id"],
            name="fk_document_chunks_organization_version",
            ondelete="CASCADE",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
    version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), index=True, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    char_start: Mapped[int] = mapped_column(Integer, nullable=False)
    char_end: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
