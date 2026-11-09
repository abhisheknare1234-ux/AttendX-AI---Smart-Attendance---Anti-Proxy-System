"""Encryption for locally stored face templates.

Only a 128-dimensional embedding is stored locally, encrypted with Fernet
(AES-128-CBC + HMAC-SHA256) under a key derived from the application's
biometric key or main secret. Raw images are never persisted.
"""
from __future__ import annotations

import base64
import json

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.core.config import Settings


class TemplateCryptoError(Exception):
    pass


def _fernet(settings: Settings) -> Fernet:
    material = (settings.face_template_key or settings.secret_key).encode("utf-8")
    key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"attendx-face-template-v1",
        info=b"local-opencv-sface",
    ).derive(material)
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_template(
    embedding: list[float],
    *,
    model_name: str,
    model_version: str,
    settings: Settings,
) -> str:
    payload = {
        "v": 1,
        "model": model_name,
        "model_version": model_version,
        "dim": len(embedding),
        "embedding": [round(float(value), 7) for value in embedding],
    }
    token = _fernet(settings).encrypt(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return token.decode("ascii")


def decrypt_template(ciphertext: str, settings: Settings) -> dict:
    try:
        raw = _fernet(settings).decrypt(ciphertext.encode("ascii"))
        payload = json.loads(raw)
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise TemplateCryptoError("The stored face template could not be decrypted.") from exc
    embedding = payload.get("embedding")
    if not isinstance(embedding, list) or not embedding:
        raise TemplateCryptoError("The stored face template is malformed.")
    return payload
