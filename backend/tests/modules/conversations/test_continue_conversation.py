from types import TracebackType
from uuid import uuid4

import pytest

from app.modules.conversations.application.chat import ChatResult
from app.modules.conversations.application.continue_conversation import (
    ContinueConversation,
    ConversationHistory,
    ConversationTurnLimitError,
    ConversationTurnRecord,
    ConversationTurnRepository,
    HistoryMessage,
    select_history,
)
from app.modules.conversations.application.queries import ConversationNotFoundError
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
        self.user_prompt = ""

    async def answer(self, system_prompt: str, user_prompt: str) -> ChatResult:
        self.user_prompt = user_prompt
        return ChatResult("Continuación respaldada [1].", 50, 7)


class FakeTurnRepository:
    def __init__(self, history: ConversationHistory | None) -> None:
        self.history = history
        self.record: ConversationTurnRecord | None = None

    async def get_history(
        self, organization_id: object, conversation_id: object, message_limit: int
    ) -> ConversationHistory | None:
        return self.history

    async def append_turn(self, record: ConversationTurnRecord, max_turns: int) -> None:
        if self.history is not None and self.history.user_message_count >= max_turns:
            raise ConversationTurnLimitError
        self.record = record


class FakeTurnUnitOfWork:
    def __init__(self, repository: FakeTurnRepository) -> None:
        self.repository: ConversationTurnRepository = repository
        self.committed = False

    async def __aenter__(self) -> "FakeTurnUnitOfWork":
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


def context() -> OrganizationContext:
    return OrganizationContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        role=Role.VIEWER,
        permissions=frozenset({Permission.COPILOT_USE}),
    )


def chunk() -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_number=1,
        document_title="Manual",
        version_id=uuid4(),
        chunk_index=0,
        page_number=2,
        content="El periodo es de quince días.",
        score=0.91,
    )


def use_case(
    history: ConversationHistory | None,
) -> tuple[ContinueConversation, FakeTurnRepository, FakeChat]:
    history_repository = FakeTurnRepository(history)
    write_repository = FakeTurnRepository(history)
    chat = FakeChat()
    return (
        ContinueConversation(
            FakeRetrieval((chunk(),)),  # type: ignore[arg-type]
            FakeTurnUnitOfWork(history_repository),
            FakeTurnUnitOfWork(write_repository),
            chat,
            retrieval_limit=5,
            max_context_characters=1000,
            history_message_limit=10,
            max_history_characters=1000,
            max_turns=20,
        ),
        write_repository,
        chat,
    )


async def test_continuation_uses_history_and_appends_turn() -> None:
    history = ConversationHistory(
        messages=(
            HistoryMessage("user", "¿Cuántos días?"),
            HistoryMessage("assistant", "Quince días [1]."),
        ),
        user_message_count=1,
    )
    handler, repository, chat = use_case(history)
    conversation_id = uuid4()
    active_context = context()

    result = await handler.execute(active_context, conversation_id, "¿Son hábiles?")

    assert result.conversation_id == conversation_id
    assert repository.record is not None
    assert repository.record.organization_id == active_context.organization_id
    assert "user: ¿Cuántos días?" in chat.user_prompt
    assert "assistant: Quince días [1]." in chat.user_prompt


async def test_continuation_hides_foreign_or_missing_conversation() -> None:
    handler, _, _ = use_case(None)

    with pytest.raises(ConversationNotFoundError):
        await handler.execute(context(), uuid4(), "Pregunta")


async def test_continuation_enforces_turn_limit_before_chat() -> None:
    handler, _, _ = use_case(ConversationHistory((), user_message_count=20))

    with pytest.raises(ConversationTurnLimitError):
        await handler.execute(context(), uuid4(), "Pregunta")


def test_history_budget_keeps_most_recent_messages() -> None:
    messages = (
        HistoryMessage("user", "a" * 8),
        HistoryMessage("assistant", "b" * 8),
        HistoryMessage("user", "c" * 8),
    )

    assert select_history(messages, 16) == messages[1:]
