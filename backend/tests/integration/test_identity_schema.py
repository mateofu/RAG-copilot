import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert, select
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.session import SessionFactory, engine
from app.modules.identity.application.bootstrap import (
    BootstrapOrganization,
    BootstrapOrganizationCommand,
)
from app.modules.identity.domain.access import Role
from app.modules.identity.infrastructure.persistence.models import (
    MembershipModel,
    OrganizationModel,
    UserModel,
)
from app.modules.identity.infrastructure.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="integration tests are disabled",
    ),
]


class IntegrationPasswordHasher:
    def hash(self, password: str) -> str:
        return f"integration-hash:{password}"


async def test_user_email_is_unique_case_insensitively() -> None:
    user_id = uuid4()
    email = f"{user_id}@example.com"

    async with engine.begin() as connection:
        await connection.execute(
            insert(UserModel).values(
                id=user_id,
                email=email.upper(),
                password_hash="test-hash",
                display_name="First User",
            )
        )

    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    insert(UserModel).values(
                        id=uuid4(),
                        email=email.lower(),
                        password_hash="test-hash",
                        display_name="Duplicate User",
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(delete(UserModel).where(UserModel.id == user_id))


async def test_membership_is_unique_per_organization_and_user() -> None:
    organization_id = uuid4()
    user_id = uuid4()

    async with engine.begin() as connection:
        await connection.execute(
            insert(OrganizationModel).values(
                id=organization_id,
                name="Test Organization",
                slug=f"test-{organization_id}",
            )
        )
        await connection.execute(
            insert(UserModel).values(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="test-hash",
                display_name="Test User",
            )
        )
        await connection.execute(
            insert(MembershipModel).values(
                id=uuid4(),
                organization_id=organization_id,
                user_id=user_id,
                role=Role.OWNER,
            )
        )

    try:
        with pytest.raises(IntegrityError):
            async with engine.begin() as connection:
                await connection.execute(
                    insert(MembershipModel).values(
                        id=uuid4(),
                        organization_id=organization_id,
                        user_id=user_id,
                        role=Role.VIEWER,
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(OrganizationModel).where(OrganizationModel.id == organization_id)
            )
            await connection.execute(delete(UserModel).where(UserModel.id == user_id))


async def test_bootstrap_persists_organization_owner_atomically() -> None:
    slug = f"bootstrap-{uuid4()}"
    email = f"{uuid4()}@example.com"
    use_case = BootstrapOrganization(
        SqlAlchemyIdentityUnitOfWork(SessionFactory),
        IntegrationPasswordHasher(),
    )

    result = await use_case.execute(
        BootstrapOrganizationCommand(
            organization_name="Bootstrap Organization",
            organization_slug=slug,
            owner_email=email,
            owner_display_name="Bootstrap Owner",
            owner_password="a sufficiently long password",
        )
    )

    try:
        async with SessionFactory() as session:
            organization = await session.scalar(
                select(OrganizationModel).where(OrganizationModel.id == result.organization_id)
            )
            user = await session.scalar(select(UserModel).where(UserModel.id == result.user_id))
            membership = await session.scalar(
                select(MembershipModel).where(MembershipModel.id == result.membership_id)
            )

        assert organization is not None
        assert organization.slug == slug
        assert user is not None
        assert user.email == email
        assert user.password_hash.startswith("integration-hash:")
        assert membership is not None
        assert membership.role is Role.OWNER
    finally:
        async with engine.begin() as connection:
            await connection.execute(
                delete(OrganizationModel).where(OrganizationModel.id == result.organization_id)
            )
            await connection.execute(delete(UserModel).where(UserModel.id == result.user_id))
