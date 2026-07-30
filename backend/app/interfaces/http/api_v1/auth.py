from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import Field

from app.interfaces.http.auth_dependencies import (
    get_authenticated_identity,
    get_organization_context,
)
from app.interfaces.http.schemas import ApiModel
from app.modules.identity.application.current_identity import (
    CurrentIdentityResult,
)
from app.modules.identity.application.login import InvalidCredentialsError, Login
from app.modules.identity.application.logout import Logout
from app.modules.identity.application.organization_context import OrganizationContext
from app.modules.identity.application.refresh import (
    InvalidRefreshTokenError,
    RefreshAccess,
)
from app.modules.identity.domain.access import Permission, Role

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(ApiModel):
    email: Annotated[str, Field(min_length=3, max_length=320)]
    password: Annotated[str, Field(min_length=1, max_length=128)]


class TokenResponse(ApiModel):
    access_token: str
    refresh_token: str
    token_type: str


class RefreshRequest(ApiModel):
    refresh_token: Annotated[str, Field(min_length=32, max_length=512)]


class MembershipResponse(ApiModel):
    organization_id: UUID
    organization_name: str
    organization_slug: str
    role: Role


class CurrentIdentityResponse(ApiModel):
    user_id: UUID
    email: str
    display_name: str
    memberships: list[MembershipResponse]


class OrganizationContextResponse(ApiModel):
    user_id: UUID
    organization_id: UUID
    role: Role
    permissions: list[Permission]


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, request: Request) -> TokenResponse:
    if request.app.state.access_token_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "authentication_not_configured"},
        )

    use_case = Login(
        unit_of_work=request.app.state.identity_uow_factory(),
        passwords=request.app.state.password_hasher,
        access_tokens=request.app.state.access_token_service,
        refresh_tokens=request.app.state.refresh_token_service,
        refresh_ttl=request.app.state.refresh_token_ttl,
        dummy_password_hash=request.app.state.dummy_password_hash,
    )
    try:
        result = await use_case.execute(payload.email, payload.password)
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": error.code,
                "message": "Invalid email or password.",
            },
            headers={"WWW-Authenticate": "Bearer"},
        ) from error

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, request: Request) -> TokenResponse:
    service = request.app.state.refresh_token_service
    use_case = RefreshAccess(
        unit_of_work=request.app.state.identity_uow_factory(),
        access_tokens=request.app.state.access_token_service,
        refresh_tokens=service,
        refresh_ttl=request.app.state.refresh_token_ttl,
    )
    try:
        result = await use_case.execute(service.digest(payload.refresh_token))
    except InvalidRefreshTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": error.code, "message": "Invalid refresh token."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from error
    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
        token_type=result.token_type,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, request: Request) -> None:
    service = request.app.state.refresh_token_service
    use_case = Logout(request.app.state.identity_uow_factory())
    await use_case.execute(service.digest(payload.refresh_token))


@router.get("/me", response_model=CurrentIdentityResponse)
async def current_identity(
    identity: Annotated[CurrentIdentityResult, Depends(get_authenticated_identity)],
) -> CurrentIdentityResponse:
    return CurrentIdentityResponse(
        user_id=identity.user_id,
        email=identity.email,
        display_name=identity.display_name,
        memberships=[
            MembershipResponse(
                organization_id=membership.organization_id,
                organization_name=membership.organization_name,
                organization_slug=membership.organization_slug,
                role=membership.role,
            )
            for membership in identity.memberships
        ],
    )


@router.get("/context", response_model=OrganizationContextResponse)
async def organization_context(
    context: Annotated[OrganizationContext, Depends(get_organization_context)],
) -> OrganizationContextResponse:
    return OrganizationContextResponse(
        user_id=context.user_id,
        organization_id=context.organization_id,
        role=context.role,
        permissions=sorted(context.permissions, key=str),
    )
