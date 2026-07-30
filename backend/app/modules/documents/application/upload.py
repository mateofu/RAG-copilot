from collections.abc import AsyncIterable, AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.modules.documents.application.ports import DocumentUnitOfWork
from app.modules.documents.application.storage import DocumentStorage
from app.modules.documents.domain.entities import (
    Document,
    DocumentVersion,
    normalize_document_title,
    normalize_pdf_filename,
)
from app.modules.documents.domain.errors import DuplicateDocumentError, InvalidPdfError
from app.modules.documents.domain.events import DocumentUploaded
from app.modules.documents.domain.status import DocumentStatus
from app.modules.identity.application.organization_context import (
    OrganizationContext,
    require_permission,
)
from app.modules.identity.domain.access import Permission

PDF_SIGNATURE = b"%PDF-"
PDF_SIGNATURE_SEARCH_LIMIT = 1024


@dataclass(frozen=True, slots=True)
class UploadDocumentCommand:
    context: OrganizationContext
    title: str
    original_filename: str
    content: AsyncIterable[bytes]


@dataclass(frozen=True, slots=True)
class UploadDocumentResult:
    document_id: UUID
    document_number: int
    version_id: UUID
    version_number: int
    title: str
    original_filename: str
    size_bytes: int
    sha256: str
    status: DocumentStatus


class UploadDocument:
    def __init__(
        self,
        unit_of_work: DocumentUnitOfWork,
        storage: DocumentStorage,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._storage = storage

    async def execute(self, command: UploadDocumentCommand) -> UploadDocumentResult:
        require_permission(command.context, Permission.DOCUMENTS_CREATE)
        title = normalize_document_title(command.title)
        filename = normalize_pdf_filename(command.original_filename)
        document_id = uuid4()
        version_id = uuid4()

        stored = await self._storage.store(
            organization_id=command.context.organization_id,
            version_id=version_id,
            content=verified_pdf_stream(command.content),
        )
        document = Document(
            id=document_id,
            organization_id=command.context.organization_id,
            title=title,
            created_by_user_id=command.context.user_id,
        )
        version = DocumentVersion(
            id=version_id,
            organization_id=command.context.organization_id,
            document_id=document_id,
            version_number=1,
            original_filename=filename,
            media_type="application/pdf",
            size_bytes=stored.size_bytes,
            sha256=stored.sha256,
            storage_key=stored.storage_key,
        )
        event = DocumentUploaded(
            event_id=uuid4(),
            occurred_at=datetime.now(UTC),
            organization_id=version.organization_id,
            document_id=document.id,
            version_id=version.id,
            version_number=version.version_number,
            storage_key=version.storage_key,
            sha256=version.sha256,
            media_type=version.media_type,
        )

        try:
            async with self._unit_of_work:
                document_number = await self._unit_of_work.repository.add(
                    document,
                    version,
                    event,
                )
                await self._unit_of_work.commit()
        except DuplicateDocumentError:
            await self._storage.delete(stored.storage_key)
            raise
        except BaseException:
            await self._storage.delete(stored.storage_key)
            raise

        return UploadDocumentResult(
            document_id=document.id,
            document_number=document_number,
            version_id=version.id,
            version_number=version.version_number,
            title=document.title,
            original_filename=version.original_filename,
            size_bytes=version.size_bytes,
            sha256=version.sha256,
            status=version.status,
        )


async def verified_pdf_stream(content: AsyncIterable[bytes]) -> AsyncIterator[bytes]:
    probe = bytearray()
    signature_verified = False

    async for chunk in content:
        if not signature_verified and len(probe) < PDF_SIGNATURE_SEARCH_LIMIT:
            remaining = PDF_SIGNATURE_SEARCH_LIMIT - len(probe)
            probe.extend(chunk[:remaining])
            signature_verified = PDF_SIGNATURE in probe
        yield chunk

    if not signature_verified:
        raise InvalidPdfError
