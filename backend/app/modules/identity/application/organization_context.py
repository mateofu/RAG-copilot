from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.application.current_identity import CurrentIdentityResult
from app.modules.identity.domain.access import Permission, Role, permissions_for


class OrganizationAccessDeniedError(Exception):
    code = "organization_access_denied"


@dataclass(frozen=True, slots=True)
class OrganizationContext:
    user_id: UUID
    organization_id: UUID
    role: Role
    permissions: frozenset[Permission]


def select_organization_context(
    identity: CurrentIdentityResult,
    organization_id: UUID,
) -> OrganizationContext:
    membership = next(
        (
            membership
            for membership in identity.memberships
            if membership.organization_id == organization_id
        ),
        None,
    )
    if membership is None:
        raise OrganizationAccessDeniedError

    return OrganizationContext(
        user_id=identity.user_id,
        organization_id=organization_id,
        role=membership.role,
        permissions=permissions_for(membership.role),
    )


def require_permission(
    context: OrganizationContext,
    permission: Permission,
) -> None:
    if permission not in context.permissions:
        raise OrganizationAccessDeniedError
