import asyncio

from celery import Celery

from app.infrastructure.outbox.publisher import PendingOutboxEvent

EVENT_TASKS = {
    "document.uploaded": "documents.ingest",
}


class CeleryEventDispatcher:
    def __init__(self, celery_app: Celery) -> None:
        self._celery_app = celery_app

    async def dispatch(self, event: PendingOutboxEvent) -> None:
        task_name = EVENT_TASKS.get(event.event_type)
        if task_name is None:
            raise ValueError("unsupported_event_type")
        await asyncio.to_thread(
            self._celery_app.send_task,
            task_name,
            kwargs={"event": event.payload},
            task_id=str(event.id),
        )
