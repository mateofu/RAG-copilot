from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

import structlog
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.infrastructure.database.session import SessionFactory, engine
from app.interfaces.http.api_v1.router import api_router
from app.modules.identity.infrastructure.passwords import Argon2PasswordHasher
from app.modules.identity.infrastructure.persistence.unit_of_work import (
    SqlAlchemyIdentityUnitOfWork,
)
from app.modules.identity.infrastructure.tokens import (
    JwtAccessTokenService,
    SecureRefreshTokenService,
)
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
    app.state.public_registration_enabled = settings.public_registration_enabled
    app.state.identity_uow_factory = lambda: SqlAlchemyIdentityUnitOfWork(SessionFactory)
    password_hasher = Argon2PasswordHasher()
    app.state.password_hasher = password_hasher
    app.state.dummy_password_hash = password_hasher.hash(
        "dummy password used only for timing defense"
    )
    app.state.refresh_token_service = SecureRefreshTokenService()
    app.state.refresh_token_ttl = timedelta(days=settings.refresh_token_ttl_days)
    app.state.access_token_service = (
        JwtAccessTokenService(
            secret=settings.jwt_secret.get_secret_value(),
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            ttl=timedelta(minutes=settings.access_token_ttl_minutes),
        )
        if settings.jwt_secret is not None
        else None
    )
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
