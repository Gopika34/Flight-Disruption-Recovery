# backend/app/core/crypto.py
import base64
import os
from cryptography.fernet import Fernet
from typing import Union

# The key must be a 32‑byte URL‑safe base64 string.
# It is read from the environment variable GITHUB_TOKEN_ENCRYPTION_KEY.
def _get_fernet() -> Fernet:
    from app.core.config import GITHUB_TOKEN_ENCRYPTION_KEY  # will be added to config
    if not GITHUB_TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("Encryption key not set (GITHUB_TOKEN_ENCRYPTION_KEY)")
    # Ensure proper padding/length
    key = GITHUB_TOKEN_ENCRYPTION_KEY.encode()
    # Fernet expects 32‑byte base64‑encoded string; validate quickly
    try:
        Fernet(key)  # will raise if malformed
    except Exception as exc:
        raise RuntimeError("Invalid GITHUB_TOKEN_ENCRYPTION_KEY") from exc
    return Fernet(key)


def encrypt(plain: Union[str, bytes]) -> str:
    """Encrypt a string/bytes and return a base64‑encoded token."""
    f = _get_fernet()
    data = plain.encode() if isinstance(plain, str) else plain
    return f.encrypt(data).decode()  # str for JSON storage


def decrypt(token: Union[str, bytes]) -> str:
    """Decrypt a token produced by encrypt() and return the plain string."""
    f = _get_fernet()
    data = token.encode() if isinstance(token, str) else token
    return f.decrypt(data).decode()