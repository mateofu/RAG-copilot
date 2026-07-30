from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.outbox.models import OutboxEventModel
from app.modules.documents.application.ingestion import IngestionVersion
from app.modules.documents.application.ports import DocumentRepository
from app.modules.documents.application.queries import DocumentSummary
from app.modules.documents.domain.chunking import TextChunk
from app.modules.documents.domain.entities import Document, DocumentVersion
from app.modules.documents.domain.errors import DuplicateDocumentError
from app.modules.documents.domain.events import DocumentUploaded
from app.modules.documents.domain.status import DocumentStatus
from app.modules.documents.infrastructure.persistence.models import (
    DocumentChunkModel,
    DocumentModel,
    DocumentVersionModel,
)


class SqlAlchemyDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(
        self,
        document: Document,
        version: DocumentVersion,
        event: DocumentUploaded,
    ) -> int:
        document_model = DocumentModel(
            id=document.id,
            organization_id=document.organization_id,
            title=document.title,
            created_by_user_id=document.created_by_user_id,
        )
        version_model = DocumentVersionModel(
            id=version.id,
            organization_id=version.organization_id,
            document_id=version.document_id,
            version_number=version.version_number,
            original_filename=version.original_filename,
            media_type=version.media_type,
            size_bytes=version.size_bytes,
            sha256=version.sha256,
            storage_key=version.storage_key,
            status=version.status,
        )
        event_model = OutboxEventModel(
            id=event.event_id,
            organization_id=event.organization_id,
            event_type="document.uploaded",
            aggregate_type="document_version",
            aggregate_id=event.version_id,
            payload={
                "eventId": str(event.event_id),
                "organizationId": str(event.organization_id),
                "documentId": str(event.document_id),
                "versionId": str(event.version_id),
                "versionNumber": event.version_number,
                "storageKey": event.storage_key,
                "sha256": event.sha256,
                "mediaType": event.media_type,
            },
            occurred_at=event.occurred_at,
        )
        self._session.add_all((document_model, version_model, event_model))
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise DuplicateDocumentError from error
        return document_model.document_number

    async def lock_version(
        self,
        organization_id: UUID,
        version_id: UUID,
    ) -> IngestionVersion | None:
        statement = (
            select(DocumentVersionModel)
            .where(
                DocumentVersionModel.organization_id == organization_id,
                DocumentVersionModel.id == version_id,
            )
            .with_for_update()
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return IngestionVersion(
            organization_id=model.organization_id,
            document_id=model.document_id,
            version_id=model.id,
            storage_key=model.storage_key,
            status=model.status,
        )

    async def mark_processing(self, version_id: UUID) -> None:
        model = await self._required_version(version_id)
        model.status = DocumentStatus.PROCESSING
        model.failure_code = None
        model.failure_message = None

    async def replace_chunks(
        self,
        version: IngestionVersion,
        chunks: tuple[TextChunk, ...],
    ) -> None:
        await self._session.execute(
            delete(DocumentChunkModel).where(
                DocumentChunkModel.organization_id == version.organization_id,
                DocumentChunkModel.version_id == version.version_id,
            )
        )
        self._session.add_all(
            DocumentChunkModel(
                id=uuid4(),
                organization_id=version.organization_id,
                document_id=version.document_id,
                version_id=version.version_id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                content=chunk.content,
            )
            for chunk in chunks
        )

    async def mark_ready(self, version_id: UUID) -> None:
        model = await self._required_version(version_id)
        model.status = DocumentStatus.READY
        model.failure_code = None
        model.failure_message = None

    async def mark_failed(self, version_id: UUID, failure_code: str) -> None:
        model = await self._required_version(version_id)
        model.status = DocumentStatus.FAILED
        model.failure_code = failure_code
        model.failure_message = None

    async def _required_version(self, version_id: UUID) -> DocumentVersionModel:
        model = await self._session.get(DocumentVersionModel, version_id)
        if model is None:
            raise RuntimeError("locked document version disappeared")
        return model

    async def list_documents(
        self,
        organization_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[DocumentSummary, ...]:
        statement = (
            select(DocumentModel, DocumentVersionModel)
            .join(
                DocumentVersionModel,
                DocumentVersionModel.document_id == DocumentModel.id,
            )
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentVersionModel.organization_id == organization_id,
            )
            .order_by(DocumentModel.document_number.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).all()
        return tuple(self._summary(document, version) for document, version in rows)

    async def count_documents(self, organization_id: UUID) -> int:
        statement = select(func.count(DocumentModel.id)).where(
            DocumentModel.organization_id == organization_id
        )
        return int(await self._session.scalar(statement) or 0)

    async def get_document(
        self,
        organization_id: UUID,
        document_number: int,
    ) -> DocumentSummary | None:
        statement = (
            select(DocumentModel, DocumentVersionModel)
            .join(
                DocumentVersionModel,
                DocumentVersionModel.document_id == DocumentModel.id,
            )
            .where(
                DocumentModel.organization_id == organization_id,
                DocumentModel.document_number == document_number,
                DocumentVersionModel.organization_id == organization_id,
            )
            .order_by(DocumentVersionModel.version_number.desc())
            .limit(1)
        )
        row = (await self._session.execute(statement)).first()
        if row is None:
            return None
        return self._summary(*row)

    @staticmethod
    def _summary(
        document: DocumentModel,
        version: DocumentVersionModel,
    ) -> DocumentSummary:
        return DocumentSummary(
            document_id=document.id,
            document_number=document.document_number,
            title=document.title,
            version_id=version.id,
            version_number=version.version_number,
            original_filename=version.original_filename,
            size_bytes=version.size_bytes,
            status=version.status,
            created_at=document.created_at,
        )
