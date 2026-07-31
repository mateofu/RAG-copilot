from types import TracebackType
from uuid import UUID, uuid4

import pytest

from app.modules.documents.application.reindex import ReindexDocuments, ReindexRepository
from app.modules.identity.application.organization_context import (
    OrganizationAccessDeniedError,
    OrganizationContext,
)
from app.modules.identity.domain.access import Permission, Role


class FakeReindexRepository:
    def __init__(self, queued: int) -> None:
        self.queued = queued
        self.organization_id: UUID | None = None
        self.force = False

    async def enqueue_reindex(
        self,
        organization_id: UUID,
        limit: int,
        force: bool,
    ) -> int:
        self.organization_id = organization_id
        self.force = force
        return self.queued


class FakeReindexUnitOfWork:
    def __init__(self, repository: FakeReindexRepository) -> None:
        self.repository: ReindexRepository = repository
        self.committed = False

    async def __aenter__(self) -> "FakeReindexUnitOfWork":
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


def context_with(*permissions: Permission) -> OrganizationContext:
    return OrganizationContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        role=Role.OWNER,
        permissions=frozenset(permissions),
    )


async def test_reindex_is_scoped_and_committed() -> None:
    repository = FakeReindexRepository(queued=3)
    unit_of_work = FakeReindexUnitOfWork(repository)
    context = context_with(Permission.DOCUMENTS_CREATE)

    result = await ReindexDocuments(unit_of_work).execute(context, 25, True)

    assert result.queued == 3
    assert repository.organization_id == context.organization_id
    assert repository.force
    assert unit_of_work.committed


async def test_reindex_requires_document_create_permission() -> None:
    unit_of_work = FakeReindexUnitOfWork(FakeReindexRepository(queued=0))

    with pytest.raises(OrganizationAccessDeniedError):
        await ReindexDocuments(unit_of_work).execute(
            context_with(Permission.DOCUMENTS_READ),
            25,
            False,
        )

    assert not unit_of_work.committed
