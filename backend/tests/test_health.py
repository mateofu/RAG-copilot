from httpx import ASGITransport, AsyncClient

from app.main import app
from app.modules.system.application.readiness import (
    DependencyReadiness,
    ReadinessResult,
)


class StubReadinessCheck:
    def __init__(self, result: ReadinessResult) -> None:
        self._result = result

    async def execute(self) -> ReadinessResult:
        return self._result


async def test_health_check() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "rag-copilot-api"}


async def test_liveness_check() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "rag-copilot-api"}


async def test_readiness_check_when_dependencies_are_ready() -> None:
    app.state.check_readiness = StubReadinessCheck(
        ReadinessResult(
            ready=True,
            dependencies=(
                DependencyReadiness(name="database", ready=True),
                DependencyReadiness(name="redis", ready=True),
            ),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": {
            "database": {"status": "up"},
            "redis": {"status": "up"},
        },
    }


async def test_readiness_check_when_a_dependency_is_down() -> None:
    app.state.check_readiness = StubReadinessCheck(
        ReadinessResult(
            ready=False,
            dependencies=(
                DependencyReadiness(name="database", ready=True),
                DependencyReadiness(name="redis", ready=False),
            ),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "dependencies": {
            "database": {"status": "up"},
            "redis": {"status": "down"},
        },
    }
