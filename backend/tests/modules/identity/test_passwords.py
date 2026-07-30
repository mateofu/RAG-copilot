from app.modules.identity.infrastructure.passwords import Argon2PasswordHasher


def test_argon2_password_round_trip() -> None:
    passwords = Argon2PasswordHasher()
    raw_password = "correct horse battery staple"

    password_hash = passwords.hash(raw_password)

    assert raw_password not in password_hash
    assert passwords.verify(raw_password, password_hash)
    assert not passwords.verify("incorrect password", password_hash)
