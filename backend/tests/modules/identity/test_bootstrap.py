from types import TracebackType

import pytest

from app.modules.identity.application.bootstrap import (
    BootstrapOrganization,
    BootstrapOrganizationCommand,
)
from app.modules.identity.application.ports import IdentityRepository
from app.modules.identity.domain.access import Role
from app.modules.identity.domain.entities import Membership, Organization, User
from app.modules.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    OrganizationSlugUnavailableError,
)


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"


class FakeIdentityRepository:
    def __init__(self) -> None:
        self.existing_slugs: set[str] = set()
        self.existing_emails: set[str] = set()
        self.organizations: list[Organization] = []
        self.users: list[User] = []
        self.memberships: list[Membership] = []

    async def organization_slug_exists(self, slug: str) -> bool:
        return slug in self.existing_slugs

    async def user_email_exists(self, email: str) -> bool:
        return email in self.existing_emails

    async def add_bootstrap(
        self,
        organization: Organization,
        user: User,
        membership: Membership,
    ) -> None:
        self.organizations.append(organization)
        self.users.append(user)
        self.memberships.append(membership)


class FakeIdentityUnitOfWork:
    def __init__(self, repository: IdentityRepository) -> None:
        self.repository = repository
        self.committed = False

    async def __aenter__(self) -> "FakeIdentityUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True


def command() -> BootstrapOrganizationCommand:
    return BootstrapOrganizationCommand(
        organization_name="  Acme Corporation  ",
        organization_slug="ACME-CORP",
        owner_email="  Owner@Example.com ",
        owner_display_name="  Ada Owner ",
        owner_password="correct horse battery staple",
    )


async def test_bootstrap_creates_normalized_owner_membership() -> None:
    repository = FakeIdentityRepository()
    unit_of_work = FakeIdentityUnitOfWork(repository)
    use_case = BootstrapOrganization(unit_of_work, FakePasswordHasher())

    result = await use_case.execute(command())

    assert unit_of_work.committed
    assert repository.organizations == [
        Organization(
            id=result.organization_id,
            name="Acme Corporation",
            slug="acme-corp",
        )
    ]
    assert repository.users == [
        User(
            id=result.user_id,
            email="owner@example.com",
            password_hash="hashed:correct horse battery staple",
            display_name="Ada Owner",
        )
    ]
    assert repository.memberships == [
        Membership(
            id=result.membership_id,
            organization_id=result.organization_id,
            user_id=result.user_id,
            role=Role.OWNER,
        )
    ]


async def test_bootstrap_rejects_existing_slug_without_writes() -> None:
    repository = FakeIdentityRepository()
    repository.existing_slugs.add("acme-corp")
    unit_of_work = FakeIdentityUnitOfWork(repository)
    use_case = BootstrapOrganization(unit_of_work, FakePasswordHasher())

    with pytest.raises(OrganizationSlugUnavailableError):
        await use_case.execute(command())

    assert not unit_of_work.committed
    assert repository.organizations == []
    assert repository.users == []
    assert repository.memberships == []


async def test_bootstrap_rejects_existing_email_without_writes() -> None:
    repository = FakeIdentityRepository()
    repository.existing_emails.add("owner@example.com")
    unit_of_work = FakeIdentityUnitOfWork(repository)
    use_case = BootstrapOrganization(unit_of_work, FakePasswordHasher())

    with pytest.raises(EmailAlreadyRegisteredError):
        await use_case.execute(command())

    assert not unit_of_work.committed
    assert repository.organizations == []
    assert repository.users == []
    assert repository.memberships == []
