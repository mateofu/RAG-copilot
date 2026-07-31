from types import TracebackType
from uuid import uuid4

from app.modules.documents.application.extraction import ExtractedPage
from app.modules.documents.application.ingestion import (
    IngestDocument,
    IngestDocumentCommand,
    IngestionRepository,
    IngestionVersion,
)
from app.modules.documents.domain.chunking import TextChunk
from app.modules.documents.domain.status import DocumentStatus


class FakeRepository:
    def __init__(self, status: DocumentStatus) -> None:
        self.version = IngestionVersion(
            organization_id=uuid4(),
            document_id=uuid4(),
            version_id=uuid4(),
            storage_key="document.pdf",
            status=status,
        )
        self.chunks: tuple[TextChunk, ...] = ()
        self.status = status

    async def lock_version(
        self,
        organization_id: object,
        version_id: object,
    ) -> IngestionVersion | None:
        return self.version

    async def mark_processing(self, version_id: object) -> None:
        self.status = DocumentStatus.PROCESSING

    async def replace_chunks(
        self,
        version: IngestionVersion,
        chunks: tuple[TextChunk, ...],
        embeddings: tuple[tuple[float, ...], ...],
        embedding_provider: str,
        embedding_model: str,
    ) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.embedding_provider = embedding_provider
        self.embedding_model = embedding_model

    async def mark_ready(self, version_id: object) -> None:
        self.status = DocumentStatus.READY

    async def mark_failed(self, version_id: object, failure_code: str) -> None:
        self.status = DocumentStatus.FAILED


class FakeUnitOfWork:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository: IngestionRepository = repository
        self.committed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


class FakeStorage:
    async def read(self, storage_key: str) -> bytes:
        return b"pdf"


class FakeExtractor:
    async def extract(self, content: bytes) -> tuple[ExtractedPage, ...]:
        return (ExtractedPage(page_number=1, text="extracted document text"),)


class FakeEmbeddings:
    dimensions = 3
    provider_name = "fake"
    model_name = "fake-v1"

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return tuple((1.0, 0.0, 0.0) for _ in texts)


async def test_ingests_pending_version() -> None:
    repository = FakeRepository(DocumentStatus.PENDING)
    unit_of_work = FakeUnitOfWork(repository)

    result = await IngestDocument(
        unit_of_work,
        FakeStorage(),  # type: ignore[arg-type]
        FakeExtractor(),
        FakeEmbeddings(),
    ).execute(
        IngestDocumentCommand(
            repository.version.organization_id,
            repository.version.version_id,
        )
    )

    assert result.status is DocumentStatus.READY
    assert result.chunk_count == 1
    assert repository.status is DocumentStatus.READY
    assert repository.embeddings == ((1.0, 0.0, 0.0),)
    assert repository.embedding_provider == "fake"
    assert repository.embedding_model == "fake-v1"
    assert unit_of_work.committed


async def test_ready_version_is_idempotent() -> None:
    repository = FakeRepository(DocumentStatus.READY)

    result = await IngestDocument(
        FakeUnitOfWork(repository),
        FakeStorage(),  # type: ignore[arg-type]
        FakeExtractor(),
        FakeEmbeddings(),
    ).execute(
        IngestDocumentCommand(
            repository.version.organization_id,
            repository.version.version_id,
        )
    )

    assert result.already_processed
    assert repository.chunks == ()
