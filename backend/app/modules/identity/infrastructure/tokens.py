import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt

from app.modules.identity.application.tokens import (
    AccessTokenClaims,
    InvalidAccessTokenError,
    RefreshToken,
)


class JwtAccessTokenService:
    def __init__(
        self,
        secret: str,
        issuer: str,
        audience: str,
        ttl: timedelta,
    ) -> None:
        if len(secret) < 32:
            raise ValueError("JWT secret must contain at least 32 characters")
        self._secret = secret
        self._issuer = issuer
        self._audience = audience
        self._ttl = ttl

    def issue(self, user_id: UUID, session_id: UUID) -> str:
        issued_at = datetime.now(UTC)
        payload = {
            "sub": str(user_id),
            "sid": str(session_id),
            "jti": str(uuid4()),
            "iss": self._issuer,
            "aud": self._audience,
            "iat": issued_at,
            "nbf": issued_at,
            "exp": issued_at + self._ttl,
        }
        return jwt.encode(payload, self._secret, algorithm="HS256")

    def decode(self, token: str) -> AccessTokenClaims:
        try:
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=self._issuer,
                options={
                    "require": ["sub", "sid", "jti", "iss", "aud", "iat", "nbf", "exp"],
                },
            )
            return AccessTokenClaims(
                user_id=UUID(payload["sub"]),
                session_id=UUID(payload["sid"]),
                token_id=UUID(payload["jti"]),
                issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
                expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
            raise InvalidAccessTokenError from error


class SecureRefreshTokenService:
    def generate(self) -> RefreshToken:
        value = secrets.token_urlsafe(48)
        return RefreshToken(value=value, digest=self.digest(value))

    def digest(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()
