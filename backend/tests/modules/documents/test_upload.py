from collections.abc import AsyncIterable, AsyncIterator
from types import TracebackType
from uuid import uuid4

import pytest

from app.modules.documents.application.ports import DocumentRepository
from app.modules.documents.application.storage import StoredDocument
from app.modules.documents.application.upload import UploadDocument, UploadDocumentCommand
from app.modules.documents.domain.entities import Document, DocumentVersion
from app.modules.documents.domain.errors import DuplicateDocumentError, InvalidPdfError
from app.modules.documents.domain.events import DocumentUploaded
from app.modules.identity.application.organization_context import (
    OrganizationAccessDeniedError,
    OrganizationContext,
)
from app.modules.identity.domain.access import Role, permissions_for


async def chunks(*values: bytes) -> AsyncIterator[bytes]:
    for value in values:
        yield value


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    async def store(
        self,
        organization_id: object,
        version_id: object,
        content: AsyncIterable[bytes],
    ) -> StoredDocument:
        payload = b"".join([chunk async for chunk in content])
        return StoredDocument(
            storage_key=f"{organization_id}/{version_id}.pdf",
            size_bytes=len(payload),
            sha256="a" * 64,
        )

    async def delete(self, storage_key: str) -> None:
        self.deleted.append(storage_key)


class FakeRepository:
    def __init__(self, duplicate: bool = False) -> None:
        self.duplicate = duplicate
        self.added: tuple[Document, DocumentVersion, DocumentUploaded] | None = None

    async def add(
        self,
        document: Document,
        version: DocumentVersion,
        event: DocumentUploaded,
    ) -> int:
        if self.duplicate:
            raise DuplicateDocumentError
        self.added = (document, version, event)
        return 42


class FakeUnitOfWork:
    def __init__(self, repository: FakeRepository) -> None:
        self.repository: DocumentRepository = repository
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


def context(role: Role) -> OrganizationContext:
    return OrganizationContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        role=role,
        permissions=permissions_for(role),
    )


async def test_uploads_pdf_and_persists_metadata() -> None:
    repository = FakeRepository()
    unit_of_work = FakeUnitOfWork(repository)
    storage = FakeStorage()

    result = await UploadDocument(unit_of_work, storage).execute(
        UploadDocumentCommand(
            context=context(Role.EDITOR),
            title="  Handbook  ",
            original_filename=r"C:\fakepath\handbook.PDF",
            content=chunks(b"%PDF-", b"content"),
        )
    )

    assert result.document_number == 42
    assert result.title == "Handbook"
    assert result.original_filename == "handbook.PDF"
    assert unit_of_work.committed
    assert repository.added is not None
    assert repository.added[2].version_id == result.version_id


async def test_viewer_cannot_upload() -> None:
    repository = FakeRepository()
    storage = FakeStorage()

    with pytest.raises(OrganizationAccessDeniedError):
        await UploadDocument(FakeUnitOfWork(repository), storage).execute(
            UploadDocumentCommand(
                context=context(Role.VIEWER),
                title="Handbook",
                original_filename="handbook.pdf",
                content=chunks(b"%PDF-content"),
            )
        )

    assert repository.added is None


async def test_rejects_content_without_pdf_signature() -> None:
    repository = FakeRepository()
    storage = FakeStorage()

    with pytest.raises(InvalidPdfError):
        await UploadDocument(FakeUnitOfWork(repository), storage).execute(
            UploadDocumentCommand(
                context=context(Role.OWNER),
                title="Not a PDF",
                original_filename="fake.pdf",
                content=chunks(b"plain text"),
            )
        )

    assert repository.added is None


async def test_duplicate_deletes_stored_file() -> None:
    repository = FakeRepository(duplicate=True)
    storage = FakeStorage()

    with pytest.raises(DuplicateDocumentError):
        await UploadDocument(FakeUnitOfWork(repository), storage).execute(
            UploadDocumentCommand(
                context=context(Role.OWNER),
                title="Duplicate",
                original_filename="duplicate.pdf",
                content=chunks(b"%PDF-content"),
            )
        )

    assert len(storage.deleted) == 1
