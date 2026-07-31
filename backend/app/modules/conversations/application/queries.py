from dataclasses import dataclass
from datetime import datetime
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.modules.identity.application.organization_context import (
    OrganizationContext,
    require_permission,
)
from app.modules.identity.domain.access import Permission


class ConversationNotFoundError(Exception):
    code = "conversation_not_found"


@dataclass(frozen=True, slots=True)
class ConversationSummary:
    conversation_id: UUID
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class CitationView:
    index: int
    chunk_id: UUID | None
    document_id: UUID
    document_number: int
    document_title: str
    version_id: UUID
    page_number: int
    content: str
    score: float


@dataclass(frozen=True, slots=True)
class MessageView:
    message_id: UUID
    role: str
    content: str
    input_tokens: int
    output_tokens: int
    created_at: datetime
    citations: tuple[CitationView, ...]


@dataclass(frozen=True, slots=True)
class ConversationDetail:
    conversation_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: tuple[MessageView, ...]


@dataclass(frozen=True, slots=True)
class ConversationPage:
    items: tuple[ConversationSummary, ...]
    total: int
    limit: int
    offset: int


class ConversationQueryRepository(Protocol):
    async def list_conversations(
        self, organization_id: UUID, limit: int, offset: int
    ) -> tuple[ConversationSummary, ...]: ...

    async def count_conversations(self, organization_id: UUID) -> int: ...

    async def get_conversation(
        self, organization_id: UUID, conversation_id: UUID
    ) -> ConversationDetail | None: ...


class ConversationQueryUnitOfWork(Protocol):
    repository: ConversationQueryRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...


class ListConversations:
    def __init__(self, unit_of_work: ConversationQueryUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self, context: OrganizationContext, limit: int, offset: int
    ) -> ConversationPage:
        require_permission(context, Permission.COPILOT_USE)
        async with self._unit_of_work:
            items = await self._unit_of_work.repository.list_conversations(
                context.organization_id, limit, offset
            )
            total = await self._unit_of_work.repository.count_conversations(context.organization_id)
        return ConversationPage(items, total, limit, offset)


class GetConversation:
    def __init__(self, unit_of_work: ConversationQueryUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(
        self, context: OrganizationContext, conversation_id: UUID
    ) -> ConversationDetail:
        require_permission(context, Permission.COPILOT_USE)
        async with self._unit_of_work:
            conversation = await self._unit_of_work.repository.get_conversation(
                context.organization_id, conversation_id
            )
        if conversation is None:
            raise ConversationNotFoundError
        return conversation
