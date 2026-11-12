
from datetime import timedelta

import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password_hashing():
    password = "TestPassword@123"

    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)

    print("Password hashing: PASSED")


def test_access_token():
    token = create_access_token("101")
    payload = decode_token(token)

    assert payload["sub"] == "101"
    assert payload["type"] == "access"
    assert "exp" in payload

    print("Access token: PASSED")


def test_refresh_token():
    token = create_refresh_token("101")
    payload = decode_token(token)

    assert payload["sub"] == "101"
    assert payload["type"] == "refresh"

    print("Refresh token: PASSED")


def test_invalid_token():
    try:
        decode_token("invalid.token.value")
        raise AssertionError("Invalid token was accepted")
    except jwt.InvalidTokenError:
        print("Invalid token rejection: PASSED")


if __name__ == "__main__":
    test_password_hashing()
    test_access_token()
    test_refresh_token()
    test_invalid_token()

    print("\nAll security tests passed!")
