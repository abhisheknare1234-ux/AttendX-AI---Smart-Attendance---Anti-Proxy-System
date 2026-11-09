"""Cryptographic helpers: Argon2id passwords, opaque tokens, signed QR payloads,
PINs, CSRF comparison and attendance references."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
import string
from datetime import datetime, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Argon2id with the argon2-cffi defaults (time_cost=3, memory_cost=64 MiB,
# parallelism=4). Re-hashing policy can be added when parameters change.
_password_hasher = PasswordHasher()
_pin_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

QR_PREFIX = "v1"


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def hash_pin(pin: str) -> str:
    return _pin_hasher.hash(pin)


def verify_pin(pin: str, pin_hash: str) -> bool:
    try:
        return _pin_hasher.verify(pin_hash, pin)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def generate_pin(length: int = 6) -> str:
    """Cryptographically secure numeric PIN with no modulo bias."""
    if length < 4:
        raise ValueError("PIN length too short")
    return "".join(str(secrets.randbelow(10)) for _ in range(length))


def generate_token(nbytes: int = 48) -> str:
    return secrets.token_urlsafe(nbytes)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def generate_reference(prefix: str = "AX") -> str:
    alphabet = string.ascii_uppercase + string.digits
    body = "".join(secrets.choice(alphabet) for _ in range(8))
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{prefix}-{date}-{body}"


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sign_qr_payload(payload: dict[str, Any], key: str) -> str:
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{QR_PREFIX}.{body}.{_b64e(signature)}"


def verify_qr_signature(token: str, key: str) -> dict[str, Any] | None:
    """Return the payload when the signature is valid, else None.

    Expiry and server-side token state are checked by the attendance service.
    """
    if not token or len(token) > 2048:
        return None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != QR_PREFIX:
        return None
    _, body, encoded_signature = parts
    expected = hmac.new(key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    try:
        provided = _b64d(encoded_signature)
    except (ValueError, binascii.Error):
        return None
    if not hmac.compare_digest(expected, provided):
        return None
    try:
        payload = json.loads(_b64d(body))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    required = {"sid", "nonce", "iat", "exp"}
    if not required.issubset(payload):
        return None
    if not all(isinstance(payload[key], str) for key in ("sid", "nonce")):
        return None
    if not all(isinstance(payload[key], int) for key in ("iat", "exp")):
        return None
    return payload


def password_problem(password: str) -> str | None:
    """Minimum provisioning policy. The admin bootstrap enforces the same rule."""
    if len(password) < 10:
        return "Password must be at least 10 characters long."
    if len(password) > 128:
        return "Password must be at most 128 characters long."
    if password.lower() == password or password.upper() == password:
        return "Password must contain both upper and lower case letters."
    if not any(ch.isdigit() for ch in password):
        return "Password must contain at least one digit."
    return None
