from types import TracebackType
from uuid import UUID, uuid4

from app.modules.documents.application.retrieval import (
    RetrievalRepository,
    SearchDocumentChunks,
)
from app.modules.identity.application.organization_context import OrganizationContext
from app.modules.identity.domain.access import Permission, Role


class FakeRetrievalRepository:
    def __init__(self) -> None:
        self.organization_id: UUID | None = None
        self.embedding: tuple[float, ...] = ()

    async def search_chunks(
        self,
        organization_id: UUID,
        embedding: tuple[float, ...],
        embedding_provider: str,
        embedding_model: str,
        limit: int,
    ) -> tuple[object, ...]:
        self.organization_id = organization_id
        self.embedding = embedding
        return ()


class FakeRetrievalUnitOfWork:
    def __init__(self, repository: FakeRetrievalRepository) -> None:
        self.repository: RetrievalRepository = repository  # type: ignore[assignment]

    async def __aenter__(self) -> "FakeRetrievalUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


class FakeEmbeddings:
    dimensions = 2
    provider_name = "fake"
    model_name = "fake-v1"

    async def embed(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        return ((0.5, 0.5),)


async def test_search_scopes_retrieval_to_active_organization() -> None:
    organization_id = uuid4()
    repository = FakeRetrievalRepository()
    context = OrganizationContext(
        user_id=uuid4(),
        organization_id=organization_id,
        role=Role.VIEWER,
        permissions=frozenset({Permission.COPILOT_USE}),
    )

    await SearchDocumentChunks(
        FakeRetrievalUnitOfWork(repository),
        FakeEmbeddings(),
    ).execute(context, "vacaciones", 5)

    assert repository.organization_id == organization_id
    assert repository.embedding == (0.5, 0.5)
