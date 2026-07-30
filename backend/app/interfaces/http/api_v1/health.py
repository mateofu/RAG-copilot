from typing import Literal

from fastapi import APIRouter, Request, Response, status
from pydantic import BaseModel

from app.modules.system.application.readiness import CheckReadiness

router = APIRouter(prefix="/health", tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class DependencyResponse(BaseModel):
    status: Literal["up", "down"]


class ReadinessResponse(BaseModel):
    status: Literal["ready", "not_ready"]
    dependencies: dict[str, DependencyResponse]


@router.get("", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(status="ok", service="rag-copilot-api")


@router.get("/live", response_model=HealthResponse)
async def liveness_check() -> HealthResponse:
    return HealthResponse(status="ok", service="rag-copilot-api")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
async def readiness_check(request: Request, response: Response) -> ReadinessResponse:
    checker: CheckReadiness = request.app.state.check_readiness
    result = await checker.execute()

    if not result.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if result.ready else "not_ready",
        dependencies={
            dependency.name: DependencyResponse(status="up" if dependency.ready else "down")
            for dependency in result.dependencies
        },
    )
