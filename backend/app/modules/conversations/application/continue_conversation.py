from dataclasses import dataclass
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID, uuid4

from app.modules.conversations.application.ask import (
    SYSTEM_PROMPT,
    AskQuestionResult,
    InvalidQuestionError,
    build_user_prompt,
    select_context,
    validate_citations,
)
from app.modules.conversations.application.chat import ChatProvider
from app.modules.conversations.application.queries import ConversationNotFoundError
from app.modules.documents.application.retrieval import RetrievedChunk, SearchDocumentChunks
from app.modules.identity.application.organization_context import (
    OrganizationContext,
    require_permission,
)
from app.modules.identity.domain.access import Permission


class ConversationTurnLimitError(Exception):
    code = "conversation_turn_limit_reached"


@dataclass(frozen=True, slots=True)
class HistoryMessage:
    role: str
    content: str


@dataclass(frozen=True, slots=True)
class ConversationHistory:
    messages: tuple[HistoryMessage, ...]
    user_message_count: int


@dataclass(frozen=True, slots=True)
class ConversationTurnRecord:
    conversation_id: UUID
    organization_id: UUID
    user_message_id: UUID
    user_content: str
    assistant_message_id: UUID
    assistant_content: str
    input_tokens: int
    output_tokens: int
    citations: tuple[RetrievedChunk, ...]


class ConversationTurnRepository(Protocol):
    async def get_history(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        message_limit: int,
    ) -> ConversationHistory | None: ...

    async def append_turn(self, record: ConversationTurnRecord, max_turns: int) -> None: ...


class ConversationTurnUnitOfWork(Protocol):
    repository: ConversationTurnRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...


class ContinueConversation:
    def __init__(
        self,
        retrieval: SearchDocumentChunks,
        history_uow: ConversationTurnUnitOfWork,
        write_uow: ConversationTurnUnitOfWork,
        chat: ChatProvider,
        retrieval_limit: int,
        max_context_characters: int,
        history_message_limit: int,
        max_history_characters: int,
        max_turns: int,
    ) -> None:
        self._retrieval = retrieval
        self._history_uow = history_uow
        self._write_uow = write_uow
        self._chat = chat
        self._retrieval_limit = retrieval_limit
        self._max_context_characters = max_context_characters
        self._history_message_limit = history_message_limit
        self._max_history_characters = max_history_characters
        self._max_turns = max_turns

    async def execute(
        self,
        context: OrganizationContext,
        conversation_id: UUID,
        question: str,
    ) -> AskQuestionResult:
        require_permission(context, Permission.COPILOT_USE)
        normalized_question = " ".join(question.split())
        if not normalized_question:
            raise InvalidQuestionError
        async with self._history_uow:
            history = await self._history_uow.repository.get_history(
                context.organization_id,
                conversation_id,
                self._history_message_limit,
            )
        if history is None:
            raise ConversationNotFoundError
        if history.user_message_count >= self._max_turns:
            raise ConversationTurnLimitError

        chunks = await self._retrieval.execute(context, normalized_question, self._retrieval_limit)
        selected = select_context(chunks, self._max_context_characters)
        prompt_history = select_history(history.messages, self._max_history_characters)
        chat_result = await self._chat.answer(
            SYSTEM_PROMPT,
            build_user_prompt(normalized_question, selected, prompt_history),
        )
        cited_chunks = validate_citations(chat_result.content, selected)
        assistant_message_id = uuid4()
        record = ConversationTurnRecord(
            conversation_id=conversation_id,
            organization_id=context.organization_id,
            user_message_id=uuid4(),
            user_content=normalized_question,
            assistant_message_id=assistant_message_id,
            assistant_content=chat_result.content,
            input_tokens=chat_result.input_tokens,
            output_tokens=chat_result.output_tokens,
            citations=cited_chunks,
        )
        async with self._write_uow:
            await self._write_uow.repository.append_turn(record, self._max_turns)
            await self._write_uow.commit()
        return AskQuestionResult(
            conversation_id=conversation_id,
            message_id=assistant_message_id,
            answer=chat_result.content,
            citations=cited_chunks,
            input_tokens=chat_result.input_tokens,
            output_tokens=chat_result.output_tokens,
        )


def select_history(
    messages: tuple[HistoryMessage, ...], max_characters: int
) -> tuple[HistoryMessage, ...]:
    selected_reversed: list[HistoryMessage] = []
    used = 0
    for message in reversed(messages):
        if used + len(message.content) > max_characters:
            continue
        selected_reversed.append(message)
        used += len(message.content)
    return tuple(reversed(selected_reversed))
