from datetime import timedelta
from uuid import uuid4

import pytest

from app.modules.identity.application.tokens import InvalidAccessTokenError
from app.modules.identity.infrastructure.tokens import (
    JwtAccessTokenService,
    SecureRefreshTokenService,
)

SECRET = "test-secret-with-at-least-32-characters"


def access_tokens() -> JwtAccessTokenService:
    return JwtAccessTokenService(
        secret=SECRET,
        issuer="test-issuer",
        audience="test-audience",
        ttl=timedelta(minutes=15),
    )


def test_access_token_round_trip() -> None:
    user_id = uuid4()
    session_id = uuid4()

    claims = access_tokens().decode(access_tokens().issue(user_id, session_id))

    assert claims.user_id == user_id
    assert claims.session_id == session_id
    assert claims.expires_at > claims.issued_at


def test_access_token_rejects_wrong_audience() -> None:
    token = access_tokens().issue(uuid4(), uuid4())
    other_audience = JwtAccessTokenService(
        secret=SECRET,
        issuer="test-issuer",
        audience="other-audience",
        ttl=timedelta(minutes=15),
    )

    with pytest.raises(InvalidAccessTokenError):
        other_audience.decode(token)


def test_access_token_rejects_wrong_secret() -> None:
    token = access_tokens().issue(uuid4(), uuid4())
    other_secret = JwtAccessTokenService(
        secret="different-secret-with-at-least-32-characters",
        issuer="test-issuer",
        audience="test-audience",
        ttl=timedelta(minutes=15),
    )

    with pytest.raises(InvalidAccessTokenError):
        other_secret.decode(token)


def test_refresh_token_is_random_and_only_digest_is_stable() -> None:
    service = SecureRefreshTokenService()

    first = service.generate()
    second = service.generate()

    assert first.value != second.value
    assert first.digest != second.digest
    assert len(first.digest) == 64
    assert service.digest(first.value) == first.digest
    assert first.value not in first.digest
