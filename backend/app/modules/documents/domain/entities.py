from dataclasses import dataclass
from pathlib import PurePosixPath
from uuid import UUID

from app.modules.documents.domain.errors import (
    InvalidDocumentFilenameError,
    InvalidDocumentTitleError,
)
from app.modules.documents.domain.status import DocumentStatus


def normalize_document_title(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 240:
        raise InvalidDocumentTitleError
    return normalized


def normalize_pdf_filename(value: str) -> str:
    normalized = PurePosixPath(value.replace("\\", "/")).name.strip()
    if (
        not 1 <= len(normalized) <= 255
        or normalized in {".", ".."}
        or not normalized.lower().endswith(".pdf")
        or any(ord(character) < 32 for character in normalized)
    ):
        raise InvalidDocumentFilenameError
    return normalized


@dataclass(frozen=True, slots=True)
class Document:
    id: UUID
    organization_id: UUID
    title: str
    created_by_user_id: UUID


@dataclass(frozen=True, slots=True)
class DocumentVersion:
    id: UUID
    organization_id: UUID
    document_id: UUID
    version_number: int
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str
    storage_key: str
    status: DocumentStatus = DocumentStatus.PENDING
