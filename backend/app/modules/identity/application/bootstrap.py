from dataclasses import dataclass
from uuid import UUID, uuid4

from app.modules.identity.application.ports import IdentityUnitOfWork, PasswordHasher
from app.modules.identity.domain.access import Role
from app.modules.identity.domain.entities import (
    Membership,
    Organization,
    User,
    normalize_display_name,
    normalize_email,
    normalize_organization_name,
    normalize_organization_slug,
    validate_password,
)
from app.modules.identity.domain.errors import (
    EmailAlreadyRegisteredError,
    OrganizationSlugUnavailableError,
)


@dataclass(frozen=True, slots=True)
class BootstrapOrganizationCommand:
    organization_name: str
    organization_slug: str
    owner_email: str
    owner_display_name: str
    owner_password: str


@dataclass(frozen=True, slots=True)
class BootstrapOrganizationResult:
    organization_id: UUID
    user_id: UUID
    membership_id: UUID


class BootstrapOrganization:
    def __init__(
        self,
        unit_of_work: IdentityUnitOfWork,
        password_hasher: PasswordHasher,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._password_hasher = password_hasher

    async def execute(
        self,
        command: BootstrapOrganizationCommand,
    ) -> BootstrapOrganizationResult:
        organization_name = normalize_organization_name(command.organization_name)
        organization_slug = normalize_organization_slug(command.organization_slug)
        owner_email = normalize_email(command.owner_email)
        owner_display_name = normalize_display_name(command.owner_display_name)
        owner_password = validate_password(command.owner_password)

        async with self._unit_of_work:
            repository = self._unit_of_work.repository
            if await repository.organization_slug_exists(organization_slug):
                raise OrganizationSlugUnavailableError
            if await repository.user_email_exists(owner_email):
                raise EmailAlreadyRegisteredError

            organization_id = uuid4()
            user_id = uuid4()
            membership_id = uuid4()

            organization = Organization(
                id=organization_id,
                name=organization_name,
                slug=organization_slug,
            )
            user = User(
                id=user_id,
                email=owner_email,
                password_hash=self._password_hasher.hash(owner_password),
                display_name=owner_display_name,
            )
            membership = Membership(
                id=membership_id,
                organization_id=organization_id,
                user_id=user_id,
                role=Role.OWNER,
            )
            await repository.add_bootstrap(
                organization,
                user,
                membership,
            )
            await self._unit_of_work.commit()

        return BootstrapOrganizationResult(
            organization_id=organization_id,
            user_id=user_id,
            membership_id=membership_id,
        )
