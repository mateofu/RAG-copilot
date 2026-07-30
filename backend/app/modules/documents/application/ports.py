from types import TracebackType
from typing import Protocol, Self

from app.modules.documents.domain.entities import Document, DocumentVersion
from app.modules.documents.domain.events import DocumentUploaded


class DocumentRepository(Protocol):
    async def add(
        self,
        document: Document,
        version: DocumentVersion,
        event: DocumentUploaded,
    ) -> int: ...


class DocumentUnitOfWork(Protocol):
    repository: DocumentRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
