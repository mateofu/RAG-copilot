from uuid import uuid4

import pytest

from app.modules.identity.application.current_identity import (
    ActiveMembership,
    CurrentIdentityResult,
)
from app.modules.identity.application.organization_context import (
    OrganizationAccessDeniedError,
    require_permission,
    select_organization_context,
)
from app.modules.identity.domain.access import Permission, Role


def build_identity(role: Role) -> tuple[CurrentIdentityResult, ActiveMembership]:
    membership = ActiveMembership(
        organization_id=uuid4(),
        organization_name="Acme",
        organization_slug="acme",
        role=role,
    )
    return (
        CurrentIdentityResult(
            user_id=uuid4(),
            email="owner@example.com",
            display_name="Owner",
            memberships=(membership,),
        ),
        membership,
    )


def test_selects_context_from_an_active_membership() -> None:
    identity, membership = build_identity(Role.OWNER)

    context = select_organization_context(identity, membership.organization_id)

    assert context.user_id == identity.user_id
    assert context.role is Role.OWNER
    assert Permission.MEMBERS_MANAGE in context.permissions


def test_rejects_an_organization_without_membership() -> None:
    identity, _ = build_identity(Role.OWNER)

    with pytest.raises(OrganizationAccessDeniedError):
        select_organization_context(identity, uuid4())


def test_rejects_a_permission_not_granted_to_the_role() -> None:
    identity, membership = build_identity(Role.VIEWER)
    context = select_organization_context(identity, membership.organization_id)

    with pytest.raises(OrganizationAccessDeniedError):
        require_permission(context, Permission.DOCUMENTS_CREATE)
