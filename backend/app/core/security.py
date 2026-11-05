"""Security, password hashing, and token authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from .config import settings

# Default secret key if not set in environment
SECRET_KEY = getattr(settings, "secret_key", "pms-insecure-development-secret-key-replace-in-prod")
TOKEN_EXPIRY_SECONDS = 3600 * 24  # 24 hours


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a random salt."""
    salt = secrets.token_hex(16)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return f"pbkdf2:sha256:{iterations}${salt}${derived.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash."""
    if not hashed_password or not hashed_password.startswith("pbkdf2:sha256:"):
        return False
    try:
        header, salt, hex_hash = hashed_password.split("$")
        iterations = int(header.split(":")[2])
        test_derived = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        )
        return hmac.compare_digest(test_derived.hex(), hex_hash)
    except Exception:
        return False


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding and padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(payload: dict[str, Any], expires_in: int = TOKEN_EXPIRY_SECONDS) -> str:
    """Create a signed JWT-compatible token with HMAC-SHA256 signature."""
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    token_payload = dict(payload)
    token_payload.setdefault("iat", now)
    token_payload.setdefault("exp", now + expires_in)

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(token_payload, separators=(",", ":")).encode("utf-8")

    segment1 = _b64url_encode(header_bytes)
    segment2 = _b64url_encode(payload_bytes)
    signing_input = f"{segment1}.{segment2}".encode("utf-8")

    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    segment3 = _b64url_encode(signature)

    return f"{segment1}.{segment2}.{segment3}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a signed JWT token. Returns payload or None if invalid."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        segment1, segment2, segment3 = parts

        signing_input = f"{segment1}.{segment2}".encode("utf-8")
        expected_sig = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = _b64url_decode(segment3)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64url_decode(segment2)
        payload = json.loads(payload_bytes.decode("utf-8"))

        # Verify expiration
        exp = payload.get("exp")
        if exp is not None and time.time() > exp:
            return None

        return payload
    except Exception:
        return None

