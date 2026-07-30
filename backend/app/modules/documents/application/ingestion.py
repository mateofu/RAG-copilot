from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.documents.application.extraction import PdfTextExtractor
from app.modules.documents.application.storage import DocumentStorage
from app.modules.documents.domain.chunking import TextChunk, chunk_pages
from app.modules.documents.domain.status import DocumentStatus


class DocumentIngestionError(Exception):
    code = "document_ingestion_failed"


class DocumentVersionNotFoundError(DocumentIngestionError):
    code = "document_version_not_found"


@dataclass(frozen=True, slots=True)
class IngestionVersion:
    organization_id: UUID
    document_id: UUID
    version_id: UUID
    storage_key: str
    status: DocumentStatus


class IngestionRepository(Protocol):
    async def lock_version(
        self,
        organization_id: UUID,
        version_id: UUID,
    ) -> IngestionVersion | None: ...

    async def mark_processing(self, version_id: UUID) -> None: ...

    async def replace_chunks(
        self,
        version: IngestionVersion,
        chunks: tuple[TextChunk, ...],
    ) -> None: ...

    async def mark_ready(self, version_id: UUID) -> None: ...

    async def mark_failed(
        self,
        version_id: UUID,
        failure_code: str,
    ) -> None: ...


class IngestionUnitOfWork(Protocol):
    repository: IngestionRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


@dataclass(frozen=True, slots=True)
class IngestDocumentCommand:
    organization_id: UUID
    version_id: UUID


@dataclass(frozen=True, slots=True)
class IngestDocumentResult:
    status: DocumentStatus
    chunk_count: int
    already_processed: bool


class IngestDocument:
    def __init__(
        self,
        unit_of_work: IngestionUnitOfWork,
        storage: DocumentStorage,
        extractor: PdfTextExtractor,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._storage = storage
        self._extractor = extractor

    async def execute(self, command: IngestDocumentCommand) -> IngestDocumentResult:
        failure: DocumentIngestionError | None = None
        result: IngestDocumentResult | None = None

        async with self._unit_of_work:
            version = await self._unit_of_work.repository.lock_version(
                command.organization_id,
                command.version_id,
            )
            if version is None:
                raise DocumentVersionNotFoundError
            if version.status is DocumentStatus.READY:
                return IngestDocumentResult(
                    status=DocumentStatus.READY,
                    chunk_count=0,
                    already_processed=True,
                )

            await self._unit_of_work.repository.mark_processing(version.version_id)
            try:
                content = await self._storage.read(version.storage_key)
                pages = await self._extractor.extract(content)
                chunks = chunk_pages(pages)
                if not chunks:
                    raise ValueError("no_extractable_text")
                await self._unit_of_work.repository.replace_chunks(version, chunks)
                await self._unit_of_work.repository.mark_ready(version.version_id)
                result = IngestDocumentResult(
                    status=DocumentStatus.READY,
                    chunk_count=len(chunks),
                    already_processed=False,
                )
            except Exception as error:
                error_code = type(error).__name__[:64]
                await self._unit_of_work.repository.mark_failed(
                    version.version_id,
                    error_code,
                )
                failure = DocumentIngestionError(error_code)
            await self._unit_of_work.commit()

        if failure is not None:
            raise failure
        if result is None:
            raise RuntimeError("ingestion completed without a result")
        return result
