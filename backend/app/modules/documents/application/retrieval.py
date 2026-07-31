from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.documents.application.embeddings import EmbeddingProvider
from app.modules.identity.application.organization_context import (
    OrganizationContext,
    require_permission,
)
from app.modules.identity.domain.access import Permission


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: UUID
    document_id: UUID
    document_number: int
    document_title: str
    version_id: UUID
    chunk_index: int
    page_number: int
    content: str
    score: float


class RetrievalRepository(Protocol):
    async def search_chunks(
        self,
        organization_id: UUID,
        embedding: tuple[float, ...],
        embedding_provider: str,
        embedding_model: str,
        limit: int,
    ) -> tuple[RetrievedChunk, ...]: ...


class RetrievalUnitOfWork(Protocol):
    repository: RetrievalRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class SearchDocumentChunks:
    def __init__(
        self,
        unit_of_work: RetrievalUnitOfWork,
        embeddings: EmbeddingProvider,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._embeddings = embeddings

    async def execute(
        self,
        context: OrganizationContext,
        query: str,
        limit: int,
    ) -> tuple[RetrievedChunk, ...]:
        require_permission(context, Permission.COPILOT_USE)
        normalized_query = query.strip()
        if not normalized_query:
            return ()
        (embedding,) = await self._embeddings.embed((normalized_query,))
        async with self._unit_of_work:
            return await self._unit_of_work.repository.search_chunks(
                context.organization_id,
                embedding,
                self._embeddings.provider_name,
                self._embeddings.model_name,
                limit,
            )
