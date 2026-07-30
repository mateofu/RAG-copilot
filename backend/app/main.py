from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.database.session import engine
from app.interfaces.http.api_v1.router import api_router
from app.modules.system.application.readiness import CheckReadiness
from app.modules.system.infrastructure.probes import DatabaseProbe, RedisProbe

settings = get_settings()
configure_logging()
logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await logger.ainfo("application_started", environment=settings.environment)
    yield
    await logger.ainfo("application_stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
    )
    app.state.check_readiness = CheckReadiness(
        probes=(DatabaseProbe(engine), RedisProbe(settings.redis_url)),
        timeout_seconds=settings.readiness_timeout_seconds,
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
