import re
from dataclasses import dataclass
from uuid import UUID

from app.modules.identity.domain.access import (
    MembershipStatus,
    OrganizationStatus,
    Role,
    UserStatus,
)
from app.modules.identity.domain.errors import (
    InvalidDisplayNameError,
    InvalidEmailError,
    InvalidOrganizationNameError,
    InvalidOrganizationSlugError,
    InvalidPasswordError,
)

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_organization_name(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 160:
        raise InvalidOrganizationNameError
    return normalized


def normalize_organization_slug(value: str) -> str:
    normalized = value.strip().lower()
    if len(normalized) > 63 or SLUG_PATTERN.fullmatch(normalized) is None:
        raise InvalidOrganizationSlugError
    return normalized


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not 3 <= len(normalized) <= 320 or any(character.isspace() for character in normalized):
        raise InvalidEmailError

    local_part, separator, domain = normalized.partition("@")
    if not separator or not local_part or not domain or "@" in domain:
        raise InvalidEmailError
    return normalized


def normalize_display_name(value: str) -> str:
    normalized = value.strip()
    if not 1 <= len(normalized) <= 120:
        raise InvalidDisplayNameError
    return normalized


def validate_password(value: str) -> str:
    if not 12 <= len(value) <= 128 or value.isspace():
        raise InvalidPasswordError
    return value


@dataclass(frozen=True, slots=True)
class Organization:
    id: UUID
    name: str
    slug: str
    status: OrganizationStatus = OrganizationStatus.ACTIVE


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    password_hash: str
    display_name: str
    status: UserStatus = UserStatus.ACTIVE
    is_email_verified: bool = False


@dataclass(frozen=True, slots=True)
class Membership:
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: Role
    status: MembershipStatus = MembershipStatus.ACTIVE
