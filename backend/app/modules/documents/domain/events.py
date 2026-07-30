from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DocumentUploaded:
    event_id: UUID
    occurred_at: datetime
    organization_id: UUID
    document_id: UUID
    version_id: UUID
    version_number: int
    storage_key: str
    sha256: str
    media_type: str
