class IdentityDomainError(ValueError):
    code = "identity_validation_error"


class InvalidOrganizationNameError(IdentityDomainError):
    code = "invalid_organization_name"


class InvalidOrganizationSlugError(IdentityDomainError):
    code = "invalid_organization_slug"


class InvalidEmailError(IdentityDomainError):
    code = "invalid_email"


class InvalidDisplayNameError(IdentityDomainError):
    code = "invalid_display_name"


class InvalidPasswordError(IdentityDomainError):
    code = "invalid_password"


class IdentityConflictError(Exception):
    code = "identity_conflict"


class OrganizationSlugUnavailableError(IdentityConflictError):
    code = "organization_slug_unavailable"


class EmailAlreadyRegisteredError(IdentityConflictError):
    code = "email_already_registered"
