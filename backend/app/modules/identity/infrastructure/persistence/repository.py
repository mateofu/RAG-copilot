from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.application.current_identity import (
    ActiveMembership,
    CurrentIdentityResult,
)
from app.modules.identity.application.login import LoginUser
from app.modules.identity.application.ports import IdentityRepository
from app.modules.identity.application.refresh import RefreshSession
from app.modules.identity.domain.access import (
    MembershipStatus,
    OrganizationStatus,
    UserStatus,
)
from app.modules.identity.domain.entities import Membership, Organization, User
from app.modules.identity.domain.errors import IdentityConflictError
from app.modules.identity.infrastructure.persistence.models import (
    AuthSessionModel,
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

    async def find_login_user(self, email: str) -> LoginUser | None:
        model = await self._session.scalar(select(UserModel).where(UserModel.email == email))
        if model is None:
            return None
        return LoginUser(id=model.id, password_hash=model.password_hash, status=model.status)

    def add_auth_session(
        self,
        session_id: UUID,
        user_id: UUID,
        family_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> None:
        self._session.add(
            AuthSessionModel(
                id=session_id,
                user_id=user_id,
                family_id=family_id,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
            )
        )

    async def lock_refresh_session(self, token_hash: str) -> RefreshSession | None:
        statement = (
            select(AuthSessionModel)
            .where(AuthSessionModel.refresh_token_hash == token_hash)
            .with_for_update()
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return RefreshSession(
            id=model.id,
            user_id=model.user_id,
            family_id=model.family_id,
            expires_at=model.expires_at,
            revoked_at=model.revoked_at,
        )

    async def rotate_session(
        self,
        current: RefreshSession,
        replacement_id: UUID,
        replacement_hash: str,
        replacement_expires_at: datetime,
        rotated_at: datetime,
    ) -> None:
        self._session.add(
            AuthSessionModel(
                id=replacement_id,
                user_id=current.user_id,
                family_id=current.family_id,
                refresh_token_hash=replacement_hash,
                expires_at=replacement_expires_at,
            )
        )
        await self._session.flush()
        model = await self._session.get(AuthSessionModel, current.id)
        if model is None:
            raise RuntimeError("locked session disappeared")
        model.revoked_at = rotated_at
        model.replaced_by_id = replacement_id

    async def revoke_session_family(self, family_id: UUID, revoked_at: datetime) -> None:
        await self._session.execute(
            update(AuthSessionModel)
            .where(
                AuthSessionModel.family_id == family_id,
                AuthSessionModel.revoked_at.is_(None),
            )
            .values(revoked_at=revoked_at)
        )

    async def get_current_identity(
        self,
        user_id: UUID,
        session_id: UUID,
        now: datetime,
    ) -> CurrentIdentityResult | None:
        session = await self._session.scalar(
            select(AuthSessionModel).where(
                AuthSessionModel.id == session_id,
                AuthSessionModel.user_id == user_id,
                AuthSessionModel.revoked_at.is_(None),
                AuthSessionModel.expires_at > now,
            )
        )
        user = await self._session.get(UserModel, user_id)
        if session is None or user is None or user.status is not UserStatus.ACTIVE:
            return None

        rows = (
            await self._session.execute(
                select(MembershipModel, OrganizationModel)
                .join(
                    OrganizationModel,
                    OrganizationModel.id == MembershipModel.organization_id,
                )
                .where(
                    MembershipModel.user_id == user_id,
                    MembershipModel.status == MembershipStatus.ACTIVE,
                    OrganizationModel.status == OrganizationStatus.ACTIVE,
                )
            )
        ).all()
        return CurrentIdentityResult(
            user_id=user.id,
            email=user.email,
            display_name=user.display_name,
            memberships=tuple(
                ActiveMembership(
                    organization_id=organization.id,
                    organization_name=organization.name,
                    organization_slug=organization.slug,
                    role=membership.role,
                )
                for membership, organization in rows
            ),
        )

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
