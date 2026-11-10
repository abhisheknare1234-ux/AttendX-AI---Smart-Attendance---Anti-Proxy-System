"""TOTP (RFC 6238) and encrypted MFA secret storage.

No external TOTP dependency is used. Secrets are encrypted at rest with Fernet
under an HKDF-derived key, so a database-only compromise does not reveal them.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
from datetime import datetime, timezone
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import Settings


class MfaCryptoError(Exception):
    pass


def generate_mfa_secret() -> str:
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    padded = secret.strip().upper() + "=" * (-len(secret.strip()) % 8)
    return base64.b32decode(padded)


def hotp(secret: str, counter: int, digits: int = 6) -> str:
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(value % (10**digits)).zfill(digits)


def totp(secret: str, *, at: datetime | None = None, step: int = 30, digits: int = 6) -> str:
    moment = at or datetime.now(timezone.utc)
    return hotp(secret, int(moment.timestamp()) // step, digits)


def verify_totp(
    secret: str,
    code: str,
    *,
    at: datetime | None = None,
    step: int = 30,
    digits: int = 6,
    window: int = 1,
) -> bool:
    normalized = "".join(character for character in code if character.isdigit())
    if len(normalized) != digits:
        return False
    moment = at or datetime.now(timezone.utc)
    counter = int(moment.timestamp()) // step
    for offset in range(-window, window + 1):
        if hmac.compare_digest(hotp(secret, counter + offset, digits), normalized):
            return True
    return False


def provisioning_uri(secret: str, email: str, issuer: str = "AttendX AI") -> str:
    label = quote(f"{issuer}:{email}")
    params = (
        f"secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
    )
    return f"otpauth://totp/{label}?{params}"


def _fernet(settings: Settings) -> Fernet:
    material = (settings.mfa_key or settings.secret_key).encode("utf-8")
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"attendx-mfa-v1",
        info=b"totp-secret",
    ).derive(material)
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_mfa_secret(secret: str, settings: Settings) -> str:
    return _fernet(settings).encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_mfa_secret(ciphertext: str, settings: Settings) -> str:
    try:
        value = _fernet(settings).decrypt(ciphertext.encode("ascii")).decode("ascii")
    except (InvalidToken, ValueError, TypeError) as exc:
        raise MfaCryptoError("The stored MFA secret could not be decrypted.") from exc
    return value
