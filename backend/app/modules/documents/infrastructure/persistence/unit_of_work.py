from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.modules.documents.application.ingestion import IngestionRepository
from app.modules.documents.application.ports import DocumentRepository
from app.modules.documents.application.queries import DocumentQueryRepository
from app.modules.documents.infrastructure.persistence.repository import (
    SqlAlchemyDocumentRepository,
)


class SqlAlchemyDocumentUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.repository: DocumentRepository

    async def __aenter__(self) -> "SqlAlchemyDocumentUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyDocumentRepository(self._session)
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


class SqlAlchemyIngestionUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.repository: IngestionRepository

    async def __aenter__(self) -> "SqlAlchemyIngestionUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyDocumentRepository(self._session)
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


class SqlAlchemyDocumentQueryUnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.repository: DocumentQueryRepository

    async def __aenter__(self) -> "SqlAlchemyDocumentQueryUnitOfWork":
        self._session = self._session_factory()
        self.repository = SqlAlchemyDocumentRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None
