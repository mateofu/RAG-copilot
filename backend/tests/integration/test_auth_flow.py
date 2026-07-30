import os
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.infrastructure.database.session import engine
from app.main import app
from app.modules.identity.infrastructure.persistence.models import (
    OrganizationModel,
    UserModel,
)
from app.modules.identity.infrastructure.tokens import JwtAccessTokenService

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS") != "true",
        reason="integration tests are disabled",
    ),
]


async def test_complete_authentication_lifecycle() -> None:
    unique = uuid4().hex
    email = f"auth-{unique}@example.com"
    slug = f"auth-{unique}"
    password = "correct horse battery staple"
    app.state.public_registration_enabled = True
    app.state.access_token_service = JwtAccessTokenService(
        secret="integration-secret-with-at-least-32-characters",
        issuer="integration",
        audience="integration-api",
        ttl=timedelta(minutes=15),
    )
    transport = ASGITransport(app=app)
    registration = None

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            registration = await client.post(
                "/api/v1/organizations",
                json={
                    "organizationName": "Authentication Test",
                    "organizationSlug": slug,
                    "ownerEmail": email,
                    "ownerDisplayName": "Authentication Owner",
                    "ownerPassword": password,
                },
            )
            assert registration.status_code == 201

            login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            assert login.status_code == 200
            original = login.json()

            identity = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {original['accessToken']}"},
            )
            assert identity.status_code == 200
            assert identity.json()["email"] == email
            assert identity.json()["memberships"][0]["role"] == "owner"
            organization_id = identity.json()["memberships"][0]["organizationId"]

            context = await client.get(
                "/api/v1/auth/context",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": organization_id,
                },
            )
            assert context.status_code == 200
            assert context.json()["organizationId"] == organization_id
            assert context.json()["role"] == "owner"
            assert "members:manage" in context.json()["permissions"]

            denied_context = await client.get(
                "/api/v1/auth/context",
                headers={
                    "Authorization": f"Bearer {original['accessToken']}",
                    "X-Organization-Id": str(uuid4()),
                },
            )
            assert denied_context.status_code == 403
            assert denied_context.json()["detail"]["code"] == "organization_access_denied"

            rotation = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": original["refreshToken"]},
            )
            assert rotation.status_code == 200
            replacement = rotation.json()
            assert replacement["refreshToken"] != original["refreshToken"]

            reuse = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": original["refreshToken"]},
            )
            assert reuse.status_code == 401
            assert reuse.json()["detail"]["code"] == "refresh_token_reused"

            revoked_family = await client.post(
                "/api/v1/auth/refresh",
                json={"refreshToken": replacement["refreshToken"]},
            )
            assert revoked_family.status_code == 401

            second_login = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": password},
            )
            second = second_login.json()
            logout = await client.post(
                "/api/v1/auth/logout",
                json={"refreshToken": second["refreshToken"]},
            )
            assert logout.status_code == 204

            identity_after_logout = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {second['accessToken']}"},
            )
            assert identity_after_logout.status_code == 401
    finally:
        async with engine.begin() as connection:
            payload = registration.json() if registration is not None else {}
            organization_id = payload.get("organizationId")
            user_id = payload.get("userId")
            if organization_id:
                await connection.execute(
                    delete(OrganizationModel).where(OrganizationModel.id == UUID(organization_id))
                )
            if user_id:
                await connection.execute(delete(UserModel).where(UserModel.id == UUID(user_id)))
