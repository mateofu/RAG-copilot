from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.identity.application.organization_context import (
    OrganizationContext,
    require_permission,
)
from app.modules.identity.domain.access import Permission


class ReindexRepository(Protocol):
    async def enqueue_reindex(
        self,
        organization_id: UUID,
        limit: int,
        force: bool,
    ) -> int: ...


class ReindexUnitOfWork(Protocol):
    repository: ReindexRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


@dataclass(frozen=True, slots=True)
class ReindexDocumentsResult:
    queued: int


class ReindexDocuments:
    def __init__(self, unit_of_work: ReindexUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self,
        context: OrganizationContext,
        limit: int,
        force: bool,
    ) -> ReindexDocumentsResult:
        require_permission(context, Permission.DOCUMENTS_CREATE)
        async with self._unit_of_work:
            queued = await self._unit_of_work.repository.enqueue_reindex(
                context.organization_id,
                limit,
                force,
            )
            await self._unit_of_work.commit()
        return ReindexDocumentsResult(queued=queued)
