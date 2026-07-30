from datetime import datetime
from types import TracebackType
from uuid import UUID, uuid4

from app.infrastructure.outbox.publisher import (
    OutboxRepository,
    PendingOutboxEvent,
    PublishOutboxEvents,
)


class FakeRepository:
    def __init__(self, events: tuple[PendingOutboxEvent, ...]) -> None:
        self.events = events
        self.published: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []

    async def claim_pending(
        self,
        now: datetime,
        batch_size: int,
    ) -> tuple[PendingOutboxEvent, ...]:
        return self.events[:batch_size]

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        self.published.append(event_id)

    async def mark_failed(
        self,
        event_id: UUID,
        available_at: datetime,
        error_code: str,
    ) -> None:
        self.failed.append((event_id, error_code))


class FakeUnitOfWork:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository: OutboxRepository = repository
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


class FakeDispatcher:
    def __init__(self, failing_id: UUID | None = None) -> None:
        self.failing_id = failing_id

    async def dispatch(self, event: PendingOutboxEvent) -> None:
        if event.id == self.failing_id:
            raise ConnectionError


async def test_publishes_and_reschedules_failures() -> None:
    first_id = uuid4()
    second_id = uuid4()
    repository = FakeRepository(
        (
            PendingOutboxEvent(first_id, "document.uploaded", {}, 0),
            PendingOutboxEvent(second_id, "document.uploaded", {}, 1),
        )
    )
    unit_of_work = FakeUnitOfWork(repository)

    result = await PublishOutboxEvents(
        unit_of_work,
        FakeDispatcher(failing_id=second_id),
    ).execute()

    assert result.published == 1
    assert result.failed == 1
    assert repository.published == [first_id]
    assert repository.failed == [(second_id, "ConnectionError")]
    assert unit_of_work.committed
