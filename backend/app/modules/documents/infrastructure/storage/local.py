import asyncio
import hashlib
import os
from collections.abc import AsyncIterable
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from app.modules.documents.application.storage import (
    DocumentStorageError,
    DocumentTooLargeError,
    EmptyDocumentError,
    StoredDocument,
)


class LocalDocumentStorage:
    def __init__(self, root: Path, max_size_bytes: int) -> None:
        self._root = root.resolve()
        self._max_size_bytes = max_size_bytes

    async def store(
        self,
        organization_id: UUID,
        version_id: UUID,
        content: AsyncIterable[bytes],
    ) -> StoredDocument:
        relative_path = Path(str(organization_id), f"{version_id}.pdf")
        destination = self._resolve_key(relative_path.as_posix())
        temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
        digest = hashlib.sha256()
        size_bytes = 0

        await asyncio.to_thread(destination.parent.mkdir, parents=True, exist_ok=True)
        try:
            stream = await asyncio.to_thread(temporary.open, "xb")
            try:
                async for chunk in content:
                    if not chunk:
                        continue
                    size_bytes += len(chunk)
                    if size_bytes > self._max_size_bytes:
                        raise DocumentTooLargeError
                    digest.update(chunk)
                    await asyncio.to_thread(stream.write, chunk)
            finally:
                await asyncio.to_thread(stream.close)

            if size_bytes == 0:
                raise EmptyDocumentError

            await asyncio.to_thread(os.replace, temporary, destination)
        except OSError as error:
            await self._unlink_if_exists(temporary)
            raise DocumentStorageError from error
        except BaseException:
            await self._unlink_if_exists(temporary)
            raise

        return StoredDocument(
            storage_key=relative_path.as_posix(),
            size_bytes=size_bytes,
            sha256=digest.hexdigest(),
        )

    async def delete(self, storage_key: str) -> None:
        path = self._resolve_key(storage_key)
        await self._unlink_if_exists(path)

    async def read(self, storage_key: str) -> bytes:
        path = self._resolve_key(storage_key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except OSError as error:
            raise DocumentStorageError from error

    def _resolve_key(self, storage_key: str) -> Path:
        key = PurePosixPath(storage_key)
        if key.is_absolute() or ".." in key.parts:
            raise DocumentStorageError
        path = self._root.joinpath(*key.parts).resolve()
        if not path.is_relative_to(self._root):
            raise DocumentStorageError
        return path

    @staticmethod
    async def _unlink_if_exists(path: Path) -> None:
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as error:
            raise DocumentStorageError from error
