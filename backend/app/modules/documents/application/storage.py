from collections.abc import AsyncIterable
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class DocumentStorageError(Exception):
    code = "document_storage_error"


class EmptyDocumentError(DocumentStorageError):
    code = "empty_document"


class DocumentTooLargeError(DocumentStorageError):
    code = "document_too_large"


@dataclass(frozen=True, slots=True)
class StoredDocument:
    storage_key: str
    size_bytes: int
    sha256: str


class DocumentStorage(Protocol):
    async def store(
        self,
        organization_id: UUID,
        version_id: UUID,
        content: AsyncIterable[bytes],
    ) -> StoredDocument: ...

    async def delete(self, storage_key: str) -> None: ...

    async def read(self, storage_key: str) -> bytes: ...
