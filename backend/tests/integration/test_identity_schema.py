import os
from uuid import uuid4

import pytest
from sqlalchemy import delete, insert
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database.session import engine
from app.modules.identity.domain.access import Role
from app.modules.identity.infrastructure.persistence.models import (
    Membership,
    Organization,
    User,
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="integration tests are disabled",
    ),
]


async def test_user_email_is_unique_case_insensitively() -> None:
    user_id = uuid4()
    email = f"{user_id}@example.com"

    async with engine.begin() as connection:
        await connection.execute(
            insert(User).values(
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
                    insert(User).values(
                        id=uuid4(),
                        email=email.lower(),
                        password_hash="test-hash",
                        display_name="Duplicate User",
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(delete(User).where(User.id == user_id))


async def test_membership_is_unique_per_organization_and_user() -> None:
    organization_id = uuid4()
    user_id = uuid4()

    async with engine.begin() as connection:
        await connection.execute(
            insert(Organization).values(
                id=organization_id,
                name="Test Organization",
                slug=f"test-{organization_id}",
            )
        )
        await connection.execute(
            insert(User).values(
                id=user_id,
                email=f"{user_id}@example.com",
                password_hash="test-hash",
                display_name="Test User",
            )
        )
        await connection.execute(
            insert(Membership).values(
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
                    insert(Membership).values(
                        id=uuid4(),
                        organization_id=organization_id,
                        user_id=user_id,
                        role=Role.VIEWER,
                    )
                )
    finally:
        async with engine.begin() as connection:
            await connection.execute(delete(Organization).where(Organization.id == organization_id))
            await connection.execute(delete(User).where(User.id == user_id))
