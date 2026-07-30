from types import TracebackType

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.identity.application.ports import IdentityRepository
from app.modules.identity.domain.entities import Membership, Organization, User


class ApiIdentityRepository:
    async def organization_slug_exists(self, slug: str) -> bool:
        return False

    async def user_email_exists(self, email: str) -> bool:
        return False

    async def add_bootstrap(
        self,
        organization: Organization,
        user: User,
        membership: Membership,
    ) -> None:
        pass


class ApiIdentityUnitOfWork:
    def __init__(self) -> None:
        self.repository: IdentityRepository = ApiIdentityRepository()

    async def __aenter__(self) -> "ApiIdentityUnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        pass


class ApiPasswordHasher:
    def hash(self, password: str) -> str:
        return "api-test-hash"


async def test_bootstrap_organization_endpoint() -> None:
    app.state.public_registration_enabled = True
    app.state.identity_uow_factory = ApiIdentityUnitOfWork
    app.state.password_hasher = ApiPasswordHasher()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/organizations",
            json={
                "organizationName": "Acme Corporation",
                "organizationSlug": "acme-corp",
                "ownerEmail": "owner@example.com",
                "ownerDisplayName": "Ada Owner",
                "ownerPassword": "correct horse battery staple",
            },
        )

    assert response.status_code == 201
    assert set(response.json()) == {
        "organizationId",
        "userId",
        "membershipId",
    }


async def test_bootstrap_organization_endpoint_can_be_disabled() -> None:
    app.state.public_registration_enabled = False
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/organizations",
            json={
                "organizationName": "Acme Corporation",
                "organizationSlug": "acme-corp",
                "ownerEmail": "owner@example.com",
                "ownerDisplayName": "Ada Owner",
                "ownerPassword": "correct horse battery staple",
            },
        )

    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "public_registration_disabled"
