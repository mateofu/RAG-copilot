from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.documents.domain.status import DocumentStatus
from app.modules.identity.application.organization_context import (
    OrganizationContext,
    require_permission,
)
from app.modules.identity.domain.access import Permission


class DocumentNotFoundError(Exception):
    code = "document_not_found"


@dataclass(frozen=True, slots=True)
class DocumentSummary:
    document_id: UUID
    document_number: int
    title: str
    version_id: UUID
    version_number: int
    original_filename: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime


class DocumentQueryRepository(Protocol):
    async def list_documents(
        self,
        organization_id: UUID,
        limit: int,
        offset: int,
    ) -> tuple[DocumentSummary, ...]: ...

    async def count_documents(self, organization_id: UUID) -> int: ...

    async def get_document(
        self,
        organization_id: UUID,
        document_number: int,
    ) -> DocumentSummary | None: ...


class DocumentQueryUnitOfWork(Protocol):
    repository: DocumentQueryRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class DocumentPage:
    items: tuple[DocumentSummary, ...]
    total: int
    limit: int
    offset: int


class ListDocuments:
    def __init__(self, unit_of_work: DocumentQueryUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        context: OrganizationContext,
        limit: int,
        offset: int,
    ) -> DocumentPage:
        require_permission(context, Permission.DOCUMENTS_READ)
        async with self._unit_of_work:
            items = await self._unit_of_work.repository.list_documents(
                context.organization_id,
                limit,
                offset,
            )
            total = await self._unit_of_work.repository.count_documents(context.organization_id)
        return DocumentPage(items=items, total=total, limit=limit, offset=offset)


class GetDocument:
    def __init__(self, unit_of_work: DocumentQueryUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        context: OrganizationContext,
        document_number: int,
    ) -> DocumentSummary:
        require_permission(context, Permission.DOCUMENTS_READ)
        async with self._unit_of_work:
            document = await self._unit_of_work.repository.get_document(
                context.organization_id,
                document_number,
            )
        if document is None:
            raise DocumentNotFoundError
        return document
