from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.modules.identity.application.current_identity import (
    CurrentIdentityResult,
    GetCurrentIdentity,
    UnauthenticatedError,
)
from app.modules.identity.application.organization_context import (
    OrganizationAccessDeniedError,
    OrganizationContext,
    select_organization_context,
)
from app.modules.identity.application.tokens import InvalidAccessTokenError

bearer = HTTPBearer(auto_error=False)


async def get_authenticated_identity(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer),
    ],
) -> CurrentIdentityResult:
    access_tokens = request.app.state.access_token_service
    if credentials is None or credentials.scheme.lower() != "bearer" or access_tokens is None:
        raise unauthenticated()

    try:
        claims = access_tokens.decode(credentials.credentials)
        return await GetCurrentIdentity(request.app.state.identity_uow_factory()).execute(claims)
    except (InvalidAccessTokenError, UnauthenticatedError) as error:
        raise unauthenticated() from error


async def get_organization_context(
    identity: Annotated[CurrentIdentityResult, Depends(get_authenticated_identity)],
    organization_id: Annotated[UUID, Header(alias="X-Organization-Id")],
) -> OrganizationContext:
    try:
        return select_organization_context(identity, organization_id)
    except OrganizationAccessDeniedError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": error.code,
                "message": "Access to this organization is denied.",
            },
        ) from error


def unauthenticated() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "unauthenticated", "message": "Authentication is required."},
        headers={"WWW-Authenticate": "Bearer"},
    )
