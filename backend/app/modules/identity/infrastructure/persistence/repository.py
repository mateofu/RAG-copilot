from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application.ports import IdentityRepository
from app.modules.identity.domain.entities import Membership, Organization, User
from app.modules.identity.domain.errors import IdentityConflictError
from app.modules.identity.infrastructure.persistence.models import (
    MembershipModel,
    OrganizationModel,
    UserModel,
)


class SqlAlchemyIdentityRepository(IdentityRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def organization_slug_exists(self, slug: str) -> bool:
        statement = select(OrganizationModel.id).where(OrganizationModel.slug == slug).limit(1)
        return (await self._session.scalar(statement)) is not None

    async def user_email_exists(self, email: str) -> bool:
        statement = select(UserModel.id).where(UserModel.email == email).limit(1)
        return (await self._session.scalar(statement)) is not None

    async def add_bootstrap(
        self,
        organization: Organization,
        user: User,
        membership: Membership,
    ) -> None:
        organization_model = OrganizationModel(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            status=organization.status,
        )
        user_model = UserModel(
            id=user.id,
            email=user.email,
            password_hash=user.password_hash,
            display_name=user.display_name,
            status=user.status,
            is_email_verified=user.is_email_verified,
        )
        self._session.add_all((organization_model, user_model))
        try:
            await self._session.flush()
        except IntegrityError as error:
            raise IdentityConflictError from error

        self._session.add(
            MembershipModel(
                id=membership.id,
                organization_id=membership.organization_id,
                user_id=membership.user_id,
                role=membership.role,
                status=membership.status,
            )
        )
