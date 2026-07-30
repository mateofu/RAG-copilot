from enum import StrEnum


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class Role(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class Permission(StrEnum):
    ORGANIZATION_READ = "organization:read"
    ORGANIZATION_UPDATE = "organization:update"
    MEMBERS_READ = "members:read"
    MEMBERS_MANAGE = "members:manage"
    DOCUMENTS_READ = "documents:read"
    DOCUMENTS_CREATE = "documents:create"
    DOCUMENTS_DELETE = "documents:delete"
    COPILOT_USE = "copilot:use"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.EDITOR: frozenset(
        {
            Permission.ORGANIZATION_READ,
            Permission.MEMBERS_READ,
            Permission.DOCUMENTS_READ,
            Permission.DOCUMENTS_CREATE,
            Permission.DOCUMENTS_DELETE,
            Permission.COPILOT_USE,
        }
    ),
    Role.VIEWER: frozenset(
        {
            Permission.ORGANIZATION_READ,
            Permission.DOCUMENTS_READ,
            Permission.COPILOT_USE,
        }
    ),
}


def permissions_for(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[role]


def role_grants(role: Role, permission: Permission) -> bool:
    return permission in permissions_for(role)
