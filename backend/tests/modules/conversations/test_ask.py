from types import TracebackType
from uuid import uuid4

import pytest

from app.modules.conversations.application.ask import (
    AskQuestion,
    ConversationRecord,
    ConversationRepository,
    InvalidQuestionError,
    validate_citations,
)
from app.modules.conversations.application.chat import (
    ChatResult,
    InvalidChatCitationsError,
)
from app.modules.documents.application.retrieval import RetrievedChunk
from app.modules.identity.application.organization_context import OrganizationContext
from app.modules.identity.domain.access import Permission, Role


class FakeRetrieval:
    def __init__(self, chunks: tuple[RetrievedChunk, ...]) -> None:
        self.chunks = chunks

    async def execute(
        self, context: OrganizationContext, query: str, limit: int
    ) -> tuple[RetrievedChunk, ...]:
        return self.chunks[:limit]


class FakeChat:
    def __init__(self) -> None:
        self.system_prompt = ""
        self.user_prompt = ""

    async def answer(self, system_prompt: str, user_prompt: str) -> ChatResult:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        return ChatResult("Respuesta con fuente [1].", 40, 8)


class FakeRepository:
    def __init__(self) -> None:
        self.record: ConversationRecord | None = None

    async def add(self, record: ConversationRecord) -> None:
        self.record = record


class FakeUnitOfWork:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository: ConversationRepository = repository
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


def chunk(content: str, page: int = 1) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_number=1,
        document_title="Manual",
        version_id=uuid4(),
        chunk_index=0,
        page_number=page,
        content=content,
        score=0.9,
    )


async def test_ask_persists_messages_usage_and_citations() -> None:
    context = OrganizationContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        role=Role.VIEWER,
        permissions=frozenset({Permission.COPILOT_USE}),
    )
    repository = FakeRepository()
    unit_of_work = FakeUnitOfWork(repository)
    chat = FakeChat()
    source = chunk("Las vacaciones son de quince días.")

    result = await AskQuestion(
        FakeRetrieval((source,)),  # type: ignore[arg-type]
        unit_of_work,
        chat,
        retrieval_limit=5,
        max_context_characters=1000,
    ).execute(context, "  ¿Cuántos   días de vacaciones? ")

    assert result.answer == "Respuesta con fuente [1]."
    assert result.citations == (source,)
    assert repository.record is not None
    assert repository.record.organization_id == context.organization_id
    assert repository.record.user_content == "¿Cuántos días de vacaciones?"
    assert repository.record.input_tokens == 40
    assert unit_of_work.committed
    assert "untrusted data" in chat.system_prompt
    assert "[1] Document: Manual; page: 1" in chat.user_prompt


async def test_ask_respects_context_character_budget() -> None:
    context = OrganizationContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        role=Role.VIEWER,
        permissions=frozenset({Permission.COPILOT_USE}),
    )
    first = chunk("a" * 8)
    second = chunk("b" * 8, page=2)

    result = await AskQuestion(
        FakeRetrieval((first, second)),  # type: ignore[arg-type]
        FakeUnitOfWork(FakeRepository()),
        FakeChat(),
        retrieval_limit=5,
        max_context_characters=10,
    ).execute(context, "Pregunta")

    assert result.citations == (first,)


def test_citations_are_exactly_the_referenced_chunks() -> None:
    first = chunk("first")
    second = chunk("second", page=2)

    citations = validate_citations("Usa la segunda [2] y de nuevo [2].", (first, second))

    assert citations == (second,)


def test_out_of_range_citation_is_rejected() -> None:
    with pytest.raises(InvalidChatCitationsError):
        validate_citations("Referencia inventada [2].", (chunk("only"),))


async def test_whitespace_only_question_is_rejected_before_retrieval() -> None:
    context = OrganizationContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        role=Role.VIEWER,
        permissions=frozenset({Permission.COPILOT_USE}),
    )

    with pytest.raises(InvalidQuestionError):
        await AskQuestion(
            FakeRetrieval(()),  # type: ignore[arg-type]
            FakeUnitOfWork(FakeRepository()),
            FakeChat(),
            retrieval_limit=5,
            max_context_characters=100,
        ).execute(context, " \n\t ")
