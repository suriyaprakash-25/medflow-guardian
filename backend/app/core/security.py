from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from passlib.context import CryptContext
import secrets
import hashlib
from cryptography.fernet import Fernet

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(
    subject: Union[str, Any],
    expires_delta: timedelta = None,
    *,
    token_type: str = "access",
    mfa_verified: bool = True,
    session_id: int | None = None,
) -> str:
    """Create a JWT with explicit authentication-stage and session claims.

    `access` tokens are usable by protected application endpoints. `preauth`
    tokens are deliberately restricted to the MFA verification endpoint and
    must never be accepted as normal bearer credentials. Production-issued
    access tokens can also carry `sid`, binding them to a revocable server-side
    authentication session.
    """
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {
        "iat": now,
        "exp": expire,
        "sub": str(subject),
        "token_type": token_type,
        "mfa_verified": mfa_verified,
    }
    if session_id is not None:
        to_encode["sid"] = session_id
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

# ---------------------------------------------------------------------------
# Refresh Token Utilities
# ---------------------------------------------------------------------------
def create_refresh_token() -> str:
    """Generate a secure random string for a refresh token."""
    return secrets.token_urlsafe(64)

def hash_refresh_token(token: str) -> str:
    """Hash the refresh token for secure database storage."""
    return hashlib.sha256(token.encode()).hexdigest()

# ---------------------------------------------------------------------------
# MFA Secrets Encryption
# ---------------------------------------------------------------------------
_fernet = Fernet(settings.ENCRYPTION_KEY)

def encrypt_mfa_secret(secret: str) -> str:
    """Encrypt a TOTP secret before storing it in the database."""
    return _fernet.encrypt(secret.encode()).decode()

def decrypt_mfa_secret(encrypted_secret: str) -> str:
    """Decrypt a TOTP secret for verification."""
    return _fernet.decrypt(encrypted_secret.encode()).decode()
