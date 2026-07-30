from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest

from app.modules.documents.application.storage import (
    DocumentStorageError,
    DocumentTooLargeError,
    EmptyDocumentError,
)
from app.modules.documents.infrastructure.storage.local import LocalDocumentStorage


async def chunks(*values: bytes) -> AsyncIterator[bytes]:
    for value in values:
        yield value


async def test_stores_stream_and_calculates_metadata(tmp_path: Path) -> None:
    organization_id = uuid4()
    version_id = uuid4()
    storage = LocalDocumentStorage(tmp_path, max_size_bytes=1024)

    result = await storage.store(
        organization_id,
        version_id,
        chunks(b"%PDF-", b"document"),
    )

    assert result.storage_key == f"{organization_id}/{version_id}.pdf"
    assert result.size_bytes == 13
    assert result.sha256 == "7ff4f244b317238d46f6c623a20b3705f0f8f3a0ef736c029580d5370db55285"
    assert (tmp_path / result.storage_key).read_bytes() == b"%PDF-document"


async def test_rejects_oversized_stream_without_leaving_a_file(
    tmp_path: Path,
) -> None:
    storage = LocalDocumentStorage(tmp_path, max_size_bytes=5)

    with pytest.raises(DocumentTooLargeError):
        await storage.store(uuid4(), uuid4(), chunks(b"123", b"456"))

    assert list(tmp_path.rglob("*.*")) == []


async def test_rejects_an_empty_stream(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path, max_size_bytes=1024)

    with pytest.raises(EmptyDocumentError):
        await storage.store(uuid4(), uuid4(), chunks(b""))

    assert list(tmp_path.rglob("*.*")) == []


async def test_delete_rejects_path_traversal(tmp_path: Path) -> None:
    storage = LocalDocumentStorage(tmp_path, max_size_bytes=1024)

    with pytest.raises(DocumentStorageError):
        await storage.delete("../secret.pdf")
