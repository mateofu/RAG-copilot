from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.conversations.application.ask import ConversationRecord
from app.modules.conversations.infrastructure.models import (
    ConversationMessageModel,
    ConversationModel,
    MessageCitationModel,
)


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
        user_message = ConversationMessageModel(
            id=record.user_message_id,
            organization_id=record.organization_id,
            conversation_id=record.conversation_id,
            role="user",
            content=record.user_content,
            input_tokens=0,
            output_tokens=0,
        )
        assistant_message = ConversationMessageModel(
            id=record.assistant_message_id,
            organization_id=record.organization_id,
            conversation_id=record.conversation_id,
            role="assistant",
            content=record.assistant_content,
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
        )
        citations = tuple(
            MessageCitationModel(
                organization_id=record.organization_id,
                message_id=record.assistant_message_id,
                chunk_id=chunk.chunk_id,
                citation_index=index,
                document_id=chunk.document_id,
                version_id=chunk.version_id,
                document_number=chunk.document_number,
                document_title=chunk.document_title,
                page_number=chunk.page_number,
                content=chunk.content,
            )
            for index, chunk in enumerate(record.citations, start=1)
        )
        self._session.add(conversation)
        await self._session.flush()
        self._session.add_all((user_message, assistant_message))
        await self._session.flush()
        self._session.add_all(citations)
        await self._session.flush()
