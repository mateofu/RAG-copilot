from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


class InvalidAccessTokenError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    user_id: UUID
    session_id: UUID
    token_id: UUID
    issued_at: datetime
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class RefreshToken:
    value: str
    digest: str
