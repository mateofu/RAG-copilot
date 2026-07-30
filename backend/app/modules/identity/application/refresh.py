from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from uuid import UUID, uuid4

from app.modules.identity.application.login import (
    AccessTokenIssuer,
    LoginResult,
    RefreshTokenIssuer,
)
from app.modules.identity.application.ports import IdentityUnitOfWork


class InvalidRefreshTokenError(Exception):
    code = "invalid_refresh_token"


class RefreshTokenReuseError(InvalidRefreshTokenError):
    code = "refresh_token_reused"


@dataclass(frozen=True, slots=True)
class RefreshSession:
    id: UUID
    user_id: UUID
    family_id: UUID
    expires_at: datetime
    revoked_at: datetime | None


class RefreshRepository(Protocol):
    async def lock_refresh_session(self, token_hash: str) -> RefreshSession | None: ...

    async def rotate_session(
        self,
        current: RefreshSession,
        replacement_id: UUID,
        replacement_hash: str,
        replacement_expires_at: datetime,
        rotated_at: datetime,
    ) -> None: ...

    async def revoke_session_family(self, family_id: UUID, revoked_at: datetime) -> None: ...


class RefreshAccess:
    def __init__(
        self,
        unit_of_work: IdentityUnitOfWork,
        access_tokens: AccessTokenIssuer,
        refresh_tokens: RefreshTokenIssuer,
        refresh_ttl: timedelta,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._access_tokens = access_tokens
        self._refresh_tokens = refresh_tokens
        self._refresh_ttl = refresh_ttl

    async def execute(self, token_hash: str) -> LoginResult:
        now = datetime.now(UTC)
        async with self._unit_of_work:
            repository = cast(RefreshRepository, self._unit_of_work.repository)
            current = await repository.lock_refresh_session(token_hash)
            if current is None or current.expires_at <= now:
                raise InvalidRefreshTokenError
            if current.revoked_at is not None:
                await repository.revoke_session_family(current.family_id, now)
                await self._unit_of_work.commit()
                raise RefreshTokenReuseError

            replacement = self._refresh_tokens.generate()
            replacement_id = uuid4()
            await repository.rotate_session(
                current=current,
                replacement_id=replacement_id,
                replacement_hash=replacement.digest,
                replacement_expires_at=now + self._refresh_ttl,
                rotated_at=now,
            )
            await self._unit_of_work.commit()

        return LoginResult(
            access_token=self._access_tokens.issue(current.user_id, replacement_id),
            refresh_token=replacement.value,
        )
