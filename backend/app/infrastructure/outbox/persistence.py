from datetime import datetime
from types import TracebackType
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.outbox.models import OutboxEventModel
from app.infrastructure.outbox.publisher import OutboxRepository, PendingOutboxEvent


class SqlAlchemyOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def claim_pending(
        self,
        now: datetime,
        batch_size: int,
    ) -> tuple[PendingOutboxEvent, ...]:
        statement = (
            select(OutboxEventModel)
            .where(
                OutboxEventModel.published_at.is_(None),
                OutboxEventModel.available_at <= now,
            )
            .order_by(OutboxEventModel.occurred_at, OutboxEventModel.id)
            .limit(batch_size)
            .with_for_update(skip_locked=True)
        )
        models = tuple((await self._session.scalars(statement)).all())
        return tuple(
            PendingOutboxEvent(
                id=model.id,
                event_type=model.event_type,
                payload=model.payload,
                attempts=model.attempts,
            )
            for model in models
        )

    async def mark_published(self, event_id: UUID, published_at: datetime) -> None:
        model = await self._required_event(event_id)
        model.published_at = published_at
        model.attempts += 1
        model.last_error = None

    async def mark_failed(
        self,
        event_id: UUID,
        available_at: datetime,
        error_code: str,
    ) -> None:
        model = await self._required_event(event_id)
        model.available_at = available_at
        model.attempts += 1
        model.last_error = error_code

    async def _required_event(self, event_id: UUID) -> OutboxEventModel:
        model = await self._session.get(OutboxEventModel, event_id)
        if model is None:
            raise RuntimeError("claimed outbox event disappeared")
        return model


class SqlAlchemyOutboxUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.repository: OutboxRepository

    async def __aenter__(self) -> "SqlAlchemyOutboxUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyOutboxRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()
        self._session = None

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("unit of work is not active")
        await self._session.commit()
