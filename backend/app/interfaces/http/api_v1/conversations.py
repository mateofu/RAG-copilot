from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import Field

from app.interfaces.http.auth_dependencies import get_organization_context
from app.interfaces.http.schemas import ApiModel
from app.modules.conversations.application.ask import AskQuestion, InvalidQuestionError
from app.modules.conversations.application.chat import ChatProviderError
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
    chunk_id: UUID
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
        raise conversation_error(
            status.HTTP_403_FORBIDDEN,
            error.code,
            "You do not have permission to use the copilot.",
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


def conversation_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, "message": message})
