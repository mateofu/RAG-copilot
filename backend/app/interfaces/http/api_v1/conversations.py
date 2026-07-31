from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import Field

from app.interfaces.http.auth_dependencies import get_organization_context
from app.interfaces.http.schemas import ApiModel
from app.modules.conversations.application.ask import (
    AskQuestion,
    AskQuestionResult,
    InvalidQuestionError,
)
from app.modules.conversations.application.chat import ChatProviderError
from app.modules.conversations.application.continue_conversation import (
    ContinueConversation,
    ConversationTurnLimitError,
)
from app.modules.conversations.application.queries import (
    CitationView,
    ConversationNotFoundError,
    GetConversation,
    ListConversations,
    MessageView,
)
from app.modules.documents.application.embeddings import EmbeddingProviderError
from app.modules.documents.application.retrieval import SearchDocumentChunks
from app.modules.identity.application.organization_context import (
    OrganizationAccessDeniedError,
    OrganizationContext,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class AskQuestionRequest(ApiModel):
    question: str = Field(min_length=1, max_length=4000)


class CitationResponse(ApiModel):
    index: int
    chunk_id: UUID | None
    document_id: UUID
    document_number: int
    document_title: str
    version_id: UUID
    page_number: int
    content: str
    score: float


class AskQuestionResponse(ApiModel):
    conversation_id: UUID
    message_id: UUID
    answer: str
    citations: list[CitationResponse]
    input_tokens: int
    output_tokens: int


class ConversationSummaryResponse(ApiModel):
    conversation_id: UUID
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(ApiModel):
    items: list[ConversationSummaryResponse]
    total: int
    limit: int
    offset: int


class MessageResponse(ApiModel):
    message_id: UUID
    role: str
    content: str
    input_tokens: int
    output_tokens: int
    created_at: datetime
    citations: list[CitationResponse]


class ConversationDetailResponse(ApiModel):
    conversation_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse]


@router.post("", response_model=AskQuestionResponse, status_code=status.HTTP_201_CREATED)
async def ask_question(
    payload: AskQuestionRequest,
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> AskQuestionResponse:
    use_case = AskQuestion(
        retrieval=SearchDocumentChunks(
            request.app.state.retrieval_uow_factory(),
            request.app.state.embedding_provider,
        ),
        conversations=request.app.state.conversation_uow_factory(),
        chat=request.app.state.chat_provider,
        retrieval_limit=request.app.state.retrieval_limit,
        max_context_characters=request.app.state.max_context_characters,
    )
    try:
        result = await use_case.execute(context, payload.question)
    except OrganizationAccessDeniedError as error:
        raise forbidden(error) from error
    except InvalidQuestionError as error:
        raise conversation_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error.code,
            "The question must contain non-whitespace characters.",
        ) from error
    except (EmbeddingProviderError, ChatProviderError) as error:
        raise conversation_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error.code,
            "The local AI provider is temporarily unavailable.",
        ) from error
    return ask_response(result)


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ConversationListResponse:
    try:
        page = await ListConversations(request.app.state.conversation_uow_factory()).execute(
            context, limit, offset
        )
    except OrganizationAccessDeniedError as error:
        raise forbidden(error) from error
    return ConversationListResponse(
        items=[
            ConversationSummaryResponse(
                conversation_id=item.conversation_id,
                title=item.title,
                message_count=item.message_count,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            for item in page.items
        ],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: UUID,
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> ConversationDetailResponse:
    try:
        detail = await GetConversation(request.app.state.conversation_uow_factory()).execute(
            context, conversation_id
        )
    except OrganizationAccessDeniedError as error:
        raise forbidden(error) from error
    except ConversationNotFoundError as error:
        raise not_found(error) from error
    return ConversationDetailResponse(
        conversation_id=detail.conversation_id,
        title=detail.title,
        created_at=detail.created_at,
        updated_at=detail.updated_at,
        messages=[message_response(message) for message in detail.messages],
    )


@router.post("/{conversation_id}/messages", response_model=AskQuestionResponse)
async def continue_conversation(
    conversation_id: UUID,
    payload: AskQuestionRequest,
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> AskQuestionResponse:
    use_case = ContinueConversation(
        retrieval=SearchDocumentChunks(
            request.app.state.retrieval_uow_factory(),
            request.app.state.embedding_provider,
        ),
        history_uow=request.app.state.conversation_uow_factory(),
        write_uow=request.app.state.conversation_uow_factory(),
        chat=request.app.state.chat_provider,
        retrieval_limit=request.app.state.retrieval_limit,
        max_context_characters=request.app.state.max_context_characters,
        history_message_limit=request.app.state.conversation_history_messages,
        max_history_characters=request.app.state.max_history_characters,
        max_turns=request.app.state.conversation_max_turns,
    )
    try:
        result = await use_case.execute(context, conversation_id, payload.question)
    except OrganizationAccessDeniedError as error:
        raise forbidden(error) from error
    except ConversationNotFoundError as error:
        raise not_found(error) from error
    except ConversationTurnLimitError as error:
        raise conversation_error(
            status.HTTP_409_CONFLICT,
            error.code,
            "The conversation has reached its configured turn limit.",
        ) from error
    except InvalidQuestionError as error:
        raise conversation_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error.code,
            "The question must contain non-whitespace characters.",
        ) from error
    except (EmbeddingProviderError, ChatProviderError) as error:
        raise conversation_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error.code,
            "The local AI provider is temporarily unavailable.",
        ) from error
    return ask_response(result)


def ask_response(result: AskQuestionResult) -> AskQuestionResponse:
    return AskQuestionResponse(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        answer=result.answer,
        citations=[
            CitationResponse(
                index=index,
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_number=chunk.document_number,
                document_title=chunk.document_title,
                version_id=chunk.version_id,
                page_number=chunk.page_number,
                content=chunk.content,
                score=chunk.score,
            )
            for index, chunk in enumerate(result.citations, start=1)
        ],
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


def message_response(message: MessageView) -> MessageResponse:
    return MessageResponse(
        message_id=message.message_id,
        role=message.role,
        content=message.content,
        input_tokens=message.input_tokens,
        output_tokens=message.output_tokens,
        created_at=message.created_at,
        citations=[citation_response(citation) for citation in message.citations],
    )


def citation_response(citation: CitationView) -> CitationResponse:
    return CitationResponse(
        index=citation.index,
        chunk_id=citation.chunk_id,
        document_id=citation.document_id,
        document_number=citation.document_number,
        document_title=citation.document_title,
        version_id=citation.version_id,
        page_number=citation.page_number,
        content=citation.content,
        score=citation.score,
    )


def not_found(error: ConversationNotFoundError) -> HTTPException:
    return conversation_error(
        status.HTTP_404_NOT_FOUND,
        error.code,
        "Conversation not found.",
    )


def forbidden(error: OrganizationAccessDeniedError) -> HTTPException:
    return conversation_error(
        status.HTTP_403_FORBIDDEN,
        error.code,
        "You do not have permission to use the copilot.",
    )


def conversation_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
