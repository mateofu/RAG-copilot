import asyncio
from uuid import UUID

from app.core.config import get_settings
from app.infrastructure.database.session import SessionFactory, engine
from app.infrastructure.outbox.persistence import SqlAlchemyOutboxUnitOfWork
from app.infrastructure.outbox.publisher import PublishOutboxEvents
from app.infrastructure.task_queue.celery_app import celery_app
from app.infrastructure.task_queue.dispatcher import CeleryEventDispatcher
from app.modules.documents.application.ingestion import (
    DocumentIngestionError,
    IngestDocument,
    IngestDocumentCommand,
)
from app.modules.documents.infrastructure.embeddings.factory import build_embedding_provider
from app.modules.documents.infrastructure.extraction.pypdf import PyPdfTextExtractor
from app.modules.documents.infrastructure.persistence.unit_of_work import (
    SqlAlchemyIngestionUnitOfWork,
)
from app.modules.documents.infrastructure.storage.local import LocalDocumentStorage


@celery_app.task(name="outbox.publish", ignore_result=True)  # type: ignore[untyped-decorator]
def publish_outbox_events() -> None:
    asyncio.run(_publish_outbox_events())


@celery_app.task(
    name="documents.ingest",
    autoretry_for=(DocumentIngestionError,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    ignore_result=True,
)  # type: ignore[untyped-decorator]
def ingest_document(event: dict[str, object]) -> None:
    asyncio.run(_ingest_document(event))


async def _publish_outbox_events() -> None:
    try:
        await PublishOutboxEvents(
            SqlAlchemyOutboxUnitOfWork(SessionFactory),
            CeleryEventDispatcher(celery_app),
        ).execute()
    finally:
        await engine.dispose()


async def _ingest_document(event: dict[str, object]) -> None:
    settings = get_settings()
    organization_id = UUID(str(event["organizationId"]))
    version_id = UUID(str(event["versionId"]))
    try:
        await IngestDocument(
            SqlAlchemyIngestionUnitOfWork(SessionFactory),
            LocalDocumentStorage(
                settings.document_storage_path,
                settings.max_document_size_bytes,
            ),
            PyPdfTextExtractor(),
            build_embedding_provider(settings),
        ).execute(
            IngestDocumentCommand(
                organization_id=organization_id,
                version_id=version_id,
            )
        )
    finally:
        await engine.dispose()
