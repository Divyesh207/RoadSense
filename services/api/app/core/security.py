import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(
    user_id: str | uuid.UUID,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """Create a signed JWT access token. Returns (token, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
        expires_in = int(expires_delta.total_seconds())
    else:
        expires_in = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        expire = now + timedelta(seconds=expires_in)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    encoded_jwt = jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed JWT access token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
        options={"require": ["sub", "exp", "iat"]},
    )


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hash of a token for secure database storage."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_refresh_token() -> tuple[str, str]:
    """Generate a cryptographically secure refresh token. Returns (raw_token, token_hash)."""
    raw_token = secrets.token_urlsafe(48)
    token_hash = hash_token(raw_token)
    return raw_token, token_hash
