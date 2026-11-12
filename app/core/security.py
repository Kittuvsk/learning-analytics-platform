
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Convert a plain-text password into an Argon2 hash."""
    return password_hasher.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:
    """Check whether a password matches its stored hash."""
    return password_hasher.verify(
        plain_password,
        hashed_password
    )


def create_token(
    subject: str,
    token_type: str,
    expires_delta: timedelta
) -> str:
    """Create a signed JWT token."""

    now = datetime.now(timezone.utc)

    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4())
    }

    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm
    )


def create_access_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.access_token_expire_minutes
        )
    )


def create_refresh_token(subject: str) -> str:
    return create_token(
        subject=subject,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.refresh_token_expire_days
        )
    )


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""

    return jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm]
    )
