from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol, cast
from uuid import UUID

from app.modules.identity.application.ports import IdentityUnitOfWork
from app.modules.identity.application.tokens import AccessTokenClaims
from app.modules.identity.domain.access import Role


class UnauthenticatedError(Exception):
    code = "unauthenticated"


@dataclass(frozen=True, slots=True)
class ActiveMembership:
    organization_id: UUID
    organization_name: str
    organization_slug: str
    role: Role


@dataclass(frozen=True, slots=True)
class CurrentIdentityResult:
    user_id: UUID
    email: str
    display_name: str
    memberships: tuple[ActiveMembership, ...]


class CurrentIdentityRepository(Protocol):
    async def get_current_identity(
        self,
        user_id: UUID,
        session_id: UUID,
        now: datetime,
    ) -> CurrentIdentityResult | None: ...


class GetCurrentIdentity:
    def __init__(self, unit_of_work: IdentityUnitOfWork) -> None:
        self._unit_of_work = unit_of_work

    async def execute(self, claims: AccessTokenClaims) -> CurrentIdentityResult:
        async with self._unit_of_work:
            repository = cast(CurrentIdentityRepository, self._unit_of_work.repository)
            identity = await repository.get_current_identity(
                user_id=claims.user_id,
                session_id=claims.session_id,
                now=datetime.now(UTC),
            )
        if identity is None:
            raise UnauthenticatedError
        return identity
