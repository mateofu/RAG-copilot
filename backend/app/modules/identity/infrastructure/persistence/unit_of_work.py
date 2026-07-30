from types import TracebackType

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.identity.application.ports import IdentityRepository
from app.modules.identity.domain.errors import IdentityConflictError
from app.modules.identity.infrastructure.persistence.repository import (
    SqlAlchemyIdentityRepository,
)


class SqlAlchemyIdentityUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.repository: IdentityRepository

    async def __aenter__(self) -> "SqlAlchemyIdentityUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyIdentityRepository(self._session)
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
        try:
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise IdentityConflictError from error
