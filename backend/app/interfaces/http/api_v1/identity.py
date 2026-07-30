from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import Field

from app.interfaces.http.schemas import ApiModel
from app.modules.identity.application.bootstrap import (
    BootstrapOrganization,
    BootstrapOrganizationCommand,
)
from app.modules.identity.domain.errors import IdentityConflictError, IdentityDomainError

router = APIRouter(prefix="/organizations", tags=["organizations"])


class BootstrapOrganizationRequest(ApiModel):
    organization_name: Annotated[str, Field(min_length=1, max_length=160)]
    organization_slug: Annotated[str, Field(min_length=1, max_length=63)]
    owner_email: Annotated[str, Field(min_length=3, max_length=320)]
    owner_display_name: Annotated[str, Field(min_length=1, max_length=120)]
    owner_password: Annotated[str, Field(min_length=12, max_length=128)]


class BootstrapOrganizationResponse(ApiModel):
    organization_id: UUID
    user_id: UUID
    membership_id: UUID


@router.post(
    "",
    response_model=BootstrapOrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def bootstrap_organization(
    payload: BootstrapOrganizationRequest,
    request: Request,
) -> BootstrapOrganizationResponse:
    if not request.app.state.public_registration_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "public_registration_disabled",
                "message": "Public organization registration is disabled.",
            },
        )

    use_case = BootstrapOrganization(
        unit_of_work=request.app.state.identity_uow_factory(),
        password_hasher=request.app.state.password_hasher,
    )
    try:
        result = await use_case.execute(
            BootstrapOrganizationCommand(
                organization_name=payload.organization_name,
                organization_slug=payload.organization_slug,
                owner_email=payload.owner_email,
                owner_display_name=payload.owner_display_name,
                owner_password=payload.owner_password,
            )
        )
    except IdentityDomainError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": error.code,
                "message": "The registration data is invalid.",
            },
        ) from error
    except IdentityConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": error.code,
                "message": "The email or organization slug is already registered.",
            },
        ) from error

    return BootstrapOrganizationResponse(
        organization_id=result.organization_id,
        user_id=result.user_id,
        membership_id=result.membership_id,
    )
