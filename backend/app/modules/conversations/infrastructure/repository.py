from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversations.application.ask import ConversationRecord
from app.modules.conversations.application.continue_conversation import (
    ConversationHistory,
    ConversationTurnLimitError,
    ConversationTurnRecord,
    HistoryMessage,
)
from app.modules.conversations.application.queries import (
    CitationView,
    ConversationDetail,
    ConversationNotFoundError,
    ConversationSummary,
    MessageView,
)
from app.modules.conversations.infrastructure.models import (
    ConversationMessageModel,
    ConversationModel,
    MessageCitationModel,
)
from app.modules.documents.application.retrieval import RetrievedChunk


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, record: ConversationRecord) -> None:
        conversation = ConversationModel(
            id=record.conversation_id,
            organization_id=record.organization_id,
            created_by_user_id=record.user_id,
            title=record.title,
        )
        self._session.add(conversation)
        await self._session.flush()
        await self._add_turn_models(
            organization_id=record.organization_id,
            conversation_id=record.conversation_id,
            user_message_id=record.user_message_id,
            user_content=record.user_content,
            assistant_message_id=record.assistant_message_id,
            assistant_content=record.assistant_content,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            citations=record.citations,
        )

    async def append_turn(self, record: ConversationTurnRecord, max_turns: int) -> None:
        conversation = await self._session.scalar(
            select(ConversationModel)
            .where(
                ConversationModel.organization_id == record.organization_id,
                ConversationModel.id == record.conversation_id,
            )
            .with_for_update()
        )
        if conversation is None:
            raise ConversationNotFoundError
        user_message_count = await self._session.scalar(
            select(func.count(ConversationMessageModel.id)).where(
                ConversationMessageModel.organization_id == record.organization_id,
                ConversationMessageModel.conversation_id == record.conversation_id,
                ConversationMessageModel.role == "user",
            )
        )
        if int(user_message_count or 0) >= max_turns:
            raise ConversationTurnLimitError
        conversation.updated_at = datetime.now(UTC)
        await self._add_turn_models(
            organization_id=record.organization_id,
            conversation_id=record.conversation_id,
            user_message_id=record.user_message_id,
            user_content=record.user_content,
            assistant_message_id=record.assistant_message_id,
            assistant_content=record.assistant_content,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            citations=record.citations,
        )

    async def get_history(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        message_limit: int,
    ) -> ConversationHistory | None:
        exists_statement = select(ConversationModel.id).where(
            ConversationModel.organization_id == organization_id,
            ConversationModel.id == conversation_id,
        )
        if await self._session.scalar(exists_statement) is None:
            return None
        message_statement = (
            select(ConversationMessageModel)
            .where(
                ConversationMessageModel.organization_id == organization_id,
                ConversationMessageModel.conversation_id == conversation_id,
            )
            .order_by(ConversationMessageModel.created_at.desc())
            .limit(message_limit)
        )
        recent = tuple((await self._session.scalars(message_statement)).all())
        user_count = await self._session.scalar(
            select(func.count(ConversationMessageModel.id)).where(
                ConversationMessageModel.organization_id == organization_id,
                ConversationMessageModel.conversation_id == conversation_id,
                ConversationMessageModel.role == "user",
            )
        )
        return ConversationHistory(
            messages=tuple(
                HistoryMessage(message.role, message.content) for message in reversed(recent)
            ),
            user_message_count=int(user_count or 0),
        )

    async def list_conversations(
        self, organization_id: UUID, limit: int, offset: int
    ) -> tuple[ConversationSummary, ...]:
        statement = (
            select(ConversationModel, func.count(ConversationMessageModel.id))
            .outerjoin(
                ConversationMessageModel,
                (ConversationMessageModel.organization_id == ConversationModel.organization_id)
                & (ConversationMessageModel.conversation_id == ConversationModel.id),
            )
            .where(ConversationModel.organization_id == organization_id)
            .group_by(ConversationModel.id)
            .order_by(ConversationModel.updated_at.desc(), ConversationModel.id)
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._session.execute(statement)).all()
        return tuple(
            ConversationSummary(
                conversation_id=model.id,
                title=model.title,
                message_count=int(message_count),
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model, message_count in rows
        )

    async def count_conversations(self, organization_id: UUID) -> int:
        return int(
            await self._session.scalar(
                select(func.count(ConversationModel.id)).where(
                    ConversationModel.organization_id == organization_id
                )
            )
            or 0
        )

    async def get_conversation(
        self, organization_id: UUID, conversation_id: UUID
    ) -> ConversationDetail | None:
        conversation = await self._session.scalar(
            select(ConversationModel).where(
                ConversationModel.organization_id == organization_id,
                ConversationModel.id == conversation_id,
            )
        )
        if conversation is None:
            return None
        messages = tuple(
            (
                await self._session.scalars(
                    select(ConversationMessageModel)
                    .where(
                        ConversationMessageModel.organization_id == organization_id,
                        ConversationMessageModel.conversation_id == conversation_id,
                    )
                    .order_by(
                        ConversationMessageModel.created_at,
                        ConversationMessageModel.id,
                    )
                )
            ).all()
        )
        message_ids = tuple(message.id for message in messages)
        citations = (
            tuple(
                (
                    await self._session.scalars(
                        select(MessageCitationModel)
                        .where(
                            MessageCitationModel.organization_id == organization_id,
                            MessageCitationModel.message_id.in_(message_ids),
                        )
                        .order_by(
                            MessageCitationModel.message_id,
                            MessageCitationModel.citation_index,
                        )
                    )
                ).all()
            )
            if message_ids
            else ()
        )
        citations_by_message: dict[UUID, list[CitationView]] = {}
        for citation in citations:
            citations_by_message.setdefault(citation.message_id, []).append(
                CitationView(
                    index=citation.citation_index,
                    chunk_id=citation.chunk_id,
                    document_id=citation.document_id,
                    document_number=citation.document_number,
                    document_title=citation.document_title,
                    version_id=citation.version_id,
                    page_number=citation.page_number,
                    content=citation.content,
                    score=citation.retrieval_score,
                )
            )
        return ConversationDetail(
            conversation_id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=tuple(
                MessageView(
                    message_id=message.id,
                    role=message.role,
                    content=message.content,
                    input_tokens=message.input_tokens,
                    output_tokens=message.output_tokens,
                    created_at=message.created_at,
                    citations=tuple(citations_by_message.get(message.id, ())),
                )
                for message in messages
            ),
        )

    async def _add_turn_models(
        self,
        organization_id: UUID,
        conversation_id: UUID,
        user_message_id: UUID,
        user_content: str,
        assistant_message_id: UUID,
        assistant_content: str,
        input_tokens: int,
        output_tokens: int,
        citations: tuple[RetrievedChunk, ...],
    ) -> None:
        turn_created_at = datetime.now(UTC)
        user_message = ConversationMessageModel(
            id=user_message_id,
            organization_id=organization_id,
            conversation_id=conversation_id,
            role="user",
            content=user_content,
            input_tokens=0,
            output_tokens=0,
            created_at=turn_created_at,
        )
        assistant_message = ConversationMessageModel(
            id=assistant_message_id,
            organization_id=organization_id,
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            created_at=turn_created_at + timedelta(microseconds=1),
        )
        citation_models = tuple(
            MessageCitationModel(
                organization_id=organization_id,
                message_id=assistant_message_id,
                chunk_id=chunk.chunk_id,
                citation_index=index,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                document_number=chunk.document_number,
                document_title=chunk.document_title,
                page_number=chunk.page_number,
                content=chunk.content,
                retrieval_score=chunk.score,
            )
            for index, chunk in enumerate(citations, start=1)
        )
        self._session.add_all((user_message, assistant_message))
        await self._session.flush()
        self._session.add_all(citation_models)
        await self._session.flush()
