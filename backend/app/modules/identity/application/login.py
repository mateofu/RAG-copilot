from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol, cast
from uuid import UUID, uuid4

from app.modules.identity.application.ports import IdentityUnitOfWork, PasswordHasher
from app.modules.identity.application.tokens import RefreshToken
from app.modules.identity.domain.access import UserStatus
from app.modules.identity.domain.entities import normalize_email
from app.modules.identity.domain.errors import InvalidEmailError


class InvalidCredentialsError(Exception):
    code = "invalid_credentials"


@dataclass(frozen=True, slots=True)
class LoginUser:
    id: UUID
    password_hash: str
    status: UserStatus


@dataclass(frozen=True, slots=True)
class LoginResult:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenIssuer(Protocol):
    def issue(self, user_id: UUID, session_id: UUID) -> str: ...


class RefreshTokenIssuer(Protocol):
    def generate(self) -> RefreshToken: ...


class LoginRepository(Protocol):
    async def find_login_user(self, email: str) -> LoginUser | None: ...

    def add_auth_session(
        self,
        session_id: UUID,
        user_id: UUID,
        family_id: UUID,
        refresh_token_hash: str,
        expires_at: datetime,
    ) -> None: ...


class Login:
    def __init__(
        self,
        unit_of_work: IdentityUnitOfWork,
        passwords: PasswordHasher,
        access_tokens: AccessTokenIssuer,
        refresh_tokens: RefreshTokenIssuer,
        refresh_ttl: timedelta,
        dummy_password_hash: str,
    ) -> None:
        self._unit_of_work = unit_of_work
        self._passwords = passwords
        self._access_tokens = access_tokens
        self._refresh_tokens = refresh_tokens
        self._refresh_ttl = refresh_ttl
        self._dummy_password_hash = dummy_password_hash

    async def execute(self, email: str, password: str) -> LoginResult:
        try:
            normalized_email = normalize_email(email)
        except InvalidEmailError as error:
            self._passwords.verify(password, self._dummy_password_hash)
            raise InvalidCredentialsError from error
        async with self._unit_of_work:
            repository = cast(LoginRepository, self._unit_of_work.repository)
            user = await repository.find_login_user(normalized_email)
            password_hash = user.password_hash if user else self._dummy_password_hash
            valid_password = self._passwords.verify(password, password_hash)
            if user is None or not valid_password or user.status is not UserStatus.ACTIVE:
                raise InvalidCredentialsError

            session_id = uuid4()
            refresh_token = self._refresh_tokens.generate()
            repository.add_auth_session(
                session_id=session_id,
                user_id=user.id,
                family_id=uuid4(),
                refresh_token_hash=refresh_token.digest,
                expires_at=datetime.now(UTC) + self._refresh_ttl,
            )
            await self._unit_of_work.commit()

        return LoginResult(
            access_token=self._access_tokens.issue(user.id, session_id),
            refresh_token=refresh_token.value,
        )
