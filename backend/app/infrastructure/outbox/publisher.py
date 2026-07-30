from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PendingOutboxEvent:
    id: UUID
    event_type: str
    payload: dict[str, object]
    attempts: int


class OutboxRepository(Protocol):
    async def claim_pending(
        self,
        now: datetime,
        batch_size: int,
    ) -> tuple[PendingOutboxEvent, ...]: ...

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None: ...

    async def mark_failed(
        self,
        event_id: UUID,
        available_at: datetime,
        error_code: str,
    ) -> None: ...


class OutboxUnitOfWork(Protocol):
    repository: OutboxRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


class EventDispatcher(Protocol):
    async def dispatch(self, event: PendingOutboxEvent) -> None: ...


@dataclass(frozen=True, slots=True)
class PublishResult:
    published: int
    failed: int


class PublishOutboxEvents:
    def __init__(
        self,
        unit_of_work: OutboxUnitOfWork,
        dispatcher: EventDispatcher,
        batch_size: int = 25,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._dispatcher = dispatcher
        self._batch_size = batch_size

    async def execute(self) -> PublishResult:
        now = datetime.now(UTC)
        published = 0
        failed = 0

        async with self._unit_of_work:
            events = await self._unit_of_work.repository.claim_pending(
                now,
                self._batch_size,
            )
            for event in events:
                try:
                    await self._dispatcher.dispatch(event)
                except Exception as error:
                    failed += 1
                    delay = min(2 ** min(event.attempts + 1, 8), 300)
                    await self._unit_of_work.repository.mark_failed(
                        event.id,
                        now + timedelta(seconds=delay),
                        type(error).__name__[:64],
                    )
                else:
                    published += 1
                    await self._unit_of_work.repository.mark_published(event.id, now)
            await self._unit_of_work.commit()

        return PublishResult(published=published, failed=failed)
