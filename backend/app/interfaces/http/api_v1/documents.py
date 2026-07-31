from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from app.interfaces.http.auth_dependencies import get_organization_context
from app.interfaces.http.schemas import ApiModel
from app.modules.documents.application.queries import (
    DocumentNotFoundError,
    DocumentSummary,
    GetDocument,
    ListDocuments,
)
from app.modules.documents.application.reindex import ReindexDocuments
from app.modules.documents.application.retrieval import RetrievedChunk, SearchDocumentChunks
from app.modules.documents.application.storage import (
    DocumentStorageError,
    DocumentTooLargeError,
    EmptyDocumentError,
)
from app.modules.documents.application.upload import UploadDocument, UploadDocumentCommand
from app.modules.documents.domain.errors import (
    DocumentError,
    DuplicateDocumentError,
    InvalidPdfError,
)
from app.modules.documents.domain.status import DocumentStatus
from app.modules.identity.application.organization_context import (
    OrganizationAccessDeniedError,
    OrganizationContext,
)

router = APIRouter(prefix="/documents", tags=["documents"])
UPLOAD_CHUNK_SIZE = 1024 * 1024


class UploadDocumentResponse(ApiModel):
    document_id: UUID
    document_number: int
    version_id: UUID
    version_number: int
    title: str
    original_filename: str
    size_bytes: int
    sha256: str
    status: DocumentStatus


class DocumentResponse(ApiModel):
    document_id: UUID
    document_number: int
    title: str
    version_id: UUID
    version_number: int
    original_filename: str
    size_bytes: int
    status: DocumentStatus
    created_at: datetime


class DocumentListResponse(ApiModel):
    items: list[DocumentResponse]
    total: int
    limit: int
    offset: int


class RetrievedChunkResponse(ApiModel):
    chunk_id: UUID
    document_id: UUID
    document_number: int
    document_title: str
    version_id: UUID
    chunk_index: int
    page_number: int
    content: str
    score: float


class DocumentSearchResponse(ApiModel):
    items: list[RetrievedChunkResponse]


class ReindexDocumentsResponse(ApiModel):
    queued: int


@router.post("", response_model=UploadDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    title: Annotated[str, Form(min_length=1, max_length=240)],
    file: Annotated[UploadFile, File()],
) -> UploadDocumentResponse:
    if file.content_type != "application/pdf" or file.filename is None:
        raise document_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "invalid_pdf",
            "Only PDF documents are accepted.",
        )

    use_case = UploadDocument(
        unit_of_work=request.app.state.document_uow_factory(),
        storage=request.app.state.document_storage,
    )
    try:
        result = await use_case.execute(
            UploadDocumentCommand(
                context=context,
                title=title,
                original_filename=file.filename,
                content=upload_chunks(file),
            )
        )
    except OrganizationAccessDeniedError as error:
        raise document_error(
            status.HTTP_403_FORBIDDEN,
            error.code,
            "You do not have permission to upload documents.",
        ) from error
    except DocumentTooLargeError as error:
        raise document_error(
            status.HTTP_413_CONTENT_TOO_LARGE,
            error.code,
            "The document exceeds the configured size limit.",
        ) from error
    except (InvalidPdfError, EmptyDocumentError) as error:
        raise document_error(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            error.code,
            "The uploaded content is not a valid PDF.",
        ) from error
    except DuplicateDocumentError as error:
        raise document_error(
            status.HTTP_409_CONFLICT,
            error.code,
            "This document already exists in the organization.",
        ) from error
    except DocumentError as error:
        raise document_error(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            error.code,
            "The document metadata is invalid.",
        ) from error
    except DocumentStorageError as error:
        raise document_error(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error.code,
            "Document storage is temporarily unavailable.",
        ) from error
    finally:
        await file.close()

    return UploadDocumentResponse(
        document_id=result.document_id,
        document_number=result.document_number,
        version_id=result.version_id,
        version_number=result.version_number,
        title=result.title,
        original_filename=result.original_filename,
        size_bytes=result.size_bytes,
        sha256=result.sha256,
        status=result.status,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DocumentListResponse:
    page = await ListDocuments(request.app.state.document_query_uow_factory()).execute(
        context,
        limit,
        offset,
    )
    return DocumentListResponse(
        items=[document_response(item) for item in page.items],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/search/chunks", response_model=DocumentSearchResponse)
async def search_document_chunks(
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    query: Annotated[str, Query(min_length=1, max_length=1000)],
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> DocumentSearchResponse:
    items = await SearchDocumentChunks(
        request.app.state.retrieval_uow_factory(),
        request.app.state.embedding_provider,
    ).execute(context, query, limit)
    return DocumentSearchResponse(items=[retrieved_chunk_response(item) for item in items])


@router.post("/reindex", response_model=ReindexDocumentsResponse)
async def reindex_documents(
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    force: bool = False,
) -> ReindexDocumentsResponse:
    try:
        result = await ReindexDocuments(request.app.state.reindex_uow_factory()).execute(
            context,
            limit,
            force,
        )
    except OrganizationAccessDeniedError as error:
        raise document_error(
            status.HTTP_403_FORBIDDEN,
            error.code,
            "You do not have permission to reindex documents.",
        ) from error
    return ReindexDocumentsResponse(queued=result.queued)


@router.get("/{document_number}", response_model=DocumentResponse)
async def get_document(
    document_number: int,
    request: Request,
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> DocumentResponse:
    try:
        document = await GetDocument(request.app.state.document_query_uow_factory()).execute(
            context, document_number
        )
    except DocumentNotFoundError as error:
        raise document_error(
            status.HTTP_404_NOT_FOUND,
            error.code,
            "Document not found.",
        ) from error
    return document_response(document)


async def upload_chunks(file: UploadFile) -> AsyncIterator[bytes]:
    while chunk := await file.read(UPLOAD_CHUNK_SIZE):
        yield chunk


def document_error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )


def document_response(document: DocumentSummary) -> DocumentResponse:
    return DocumentResponse(
        document_id=document.document_id,
        document_number=document.document_number,
        title=document.title,
        version_id=document.version_id,
        version_number=document.version_number,
        original_filename=document.original_filename,
        size_bytes=document.size_bytes,
        status=document.status,
        created_at=document.created_at,
    )


def retrieved_chunk_response(chunk: RetrievedChunk) -> RetrievedChunkResponse:
    return RetrievedChunkResponse(
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_number=chunk.document_number,
        document_title=chunk.document_title,
        version_id=chunk.version_id,
        chunk_index=chunk.chunk_index,
        page_number=chunk.page_number,
        content=chunk.content,
        score=chunk.score,
    )
