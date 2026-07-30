import pytest

from app.modules.identity.domain.access import Permission, Role, permissions_for, role_grants


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (Role.OWNER, Permission.MEMBERS_MANAGE),
        (Role.EDITOR, Permission.DOCUMENTS_CREATE),
        (Role.VIEWER, Permission.DOCUMENTS_READ),
    ],
)
def test_role_grants_expected_permissions(role: Role, permission: Permission) -> None:
    assert role_grants(role, permission)


@pytest.mark.parametrize(
    ("role", "permission"),
    [
        (Role.EDITOR, Permission.MEMBERS_MANAGE),
        (Role.VIEWER, Permission.DOCUMENTS_CREATE),
        (Role.VIEWER, Permission.ORGANIZATION_UPDATE),
    ],
)
def test_role_rejects_privileged_permissions(role: Role, permission: Permission) -> None:
    assert not role_grants(role, permission)


def test_owner_receives_every_permission() -> None:
    assert permissions_for(Role.OWNER) == frozenset(Permission)
