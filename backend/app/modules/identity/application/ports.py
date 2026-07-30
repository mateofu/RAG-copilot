from types import TracebackType
from typing import Protocol, Self

from app.modules.identity.domain.entities import Membership, Organization, User


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str) -> bool: ...


class IdentityRepository(Protocol):
    async def organization_slug_exists(self, slug: str) -> bool: ...

    async def user_email_exists(self, email: str) -> bool: ...

    async def add_bootstrap(
        self,
        organization: Organization,
        user: User,
        membership: Membership,
    ) -> None: ...


class IdentityUnitOfWork(Protocol):
    repository: IdentityRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...
