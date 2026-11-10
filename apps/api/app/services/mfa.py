"""TOTP MFA enrollment and login challenges."""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings
from app.core.security import generate_token, token_hash, verify_password
from app.core.timeutil import utcnow
from app.core.totp import (
    MfaCryptoError,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    generate_mfa_secret,
    provisioning_uri,
    verify_totp,
)
from app.models import MfaChallenge, SecuritySeverity, User, UserStatus
from app.services import audit as audit_service
from app.services import auth as auth_service


def create_challenge(
    db: Session, *, user: User, ip_address: str | None, settings: Settings
) -> tuple[str, MfaChallenge]:
    raw_token = generate_token(32)
    challenge = MfaChallenge(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        expires_at=utcnow() + timedelta(minutes=settings.mfa_challenge_ttl_minutes),
        ip_address=ip_address,
    )
    db.add(challenge)
    audit_service.security(
        db,
        event_type="MFA_CHALLENGE_ISSUED",
        severity=SecuritySeverity.INFO,
        user_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(challenge)
    return raw_token, challenge


def verify_challenge(
    db: Session,
    *,
    challenge_token: str,
    code: str,
    ip_address: str | None,
    user_agent: str | None,
    settings: Settings,
) -> tuple[User, object, str]:
    challenge = db.scalar(
        select(MfaChallenge).where(MfaChallenge.token_hash == token_hash(challenge_token))
    )
    now = utcnow()
    if challenge is None or challenge.consumed_at is not None or challenge.expires_at <= now:
        raise errors.unauthorized("The multi-factor challenge is invalid or has expired.")
    user = db.get(User, challenge.user_id)
    if user is None or user.status != UserStatus.ACTIVE or not user.mfa_enabled:
        raise errors.unauthorized("The multi-factor challenge is no longer valid.")
    if user.mfa_secret_ciphertext is None:
        raise errors.conflict(
            "This account has no usable MFA secret. Contact an administrator.", "MFA_STATE_INVALID"
        )
    try:
        secret = decrypt_mfa_secret(user.mfa_secret_ciphertext, settings)
    except MfaCryptoError:
        raise errors.conflict(
            "The MFA secret could not be read. Contact an administrator.", "MFA_STATE_INVALID"
        )
    challenge.attempts += 1
    if not verify_totp(secret, code):
        if challenge.attempts >= settings.mfa_max_attempts:
            challenge.consumed_at = now
        audit_service.security(
            db,
            event_type="MFA_VERIFICATION_FAILED",
            severity=SecuritySeverity.MEDIUM,
            user_id=user.id,
            ip_address=ip_address,
            details={"attempts": challenge.attempts},
        )
        db.commit()
        raise errors.bad_request("Incorrect authenticator code.", "MFA_CODE_INVALID")

    challenge.consumed_at = now
    session, raw_token = auth_service.start_session(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        settings=settings,
        event_type="LOGIN_SUCCEEDED_MFA",
    )
    audit_service.security(
        db,
        event_type="MFA_VERIFIED",
        severity=SecuritySeverity.INFO,
        user_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    return user, session, raw_token


def begin_setup(db: Session, *, user: User, settings: Settings) -> tuple[str, str]:
    if user.mfa_enabled:
        raise errors.conflict("MFA is already enabled for this account.", "MFA_ALREADY_ENABLED")
    secret = generate_mfa_secret()
    user.mfa_secret_ciphertext = encrypt_mfa_secret(secret, settings)
    user.mfa_enabled = False
    audit_service.audit(
        db,
        actor_user_id=user.id,
        action="MFA_SETUP_STARTED",
        entity_type="user",
        entity_id=user.id,
        details={},
    )
    db.commit()
    return secret, provisioning_uri(secret, user.email)


def enable(db: Session, *, user: User, code: str, settings: Settings) -> None:
    if user.mfa_enabled:
        raise errors.conflict("MFA is already enabled.", "MFA_ALREADY_ENABLED")
    if not user.mfa_secret_ciphertext:
        raise errors.bad_request("Start authenticator setup first.", "MFA_NOT_SETUP")
    try:
        secret = decrypt_mfa_secret(user.mfa_secret_ciphertext, settings)
    except MfaCryptoError:
        raise errors.conflict("The pending MFA secret is unreadable.", "MFA_STATE_INVALID")
    if not verify_totp(secret, code):
        audit_service.security(
            db,
            event_type="MFA_ENROLLMENT_FAILED",
            severity=SecuritySeverity.LOW,
            user_id=user.id,
        )
        db.commit()
        raise errors.bad_request("Incorrect authenticator code.", "MFA_CODE_INVALID")
    user.mfa_enabled = True
    user.mfa_enrolled_at = utcnow()
    audit_service.audit(
        db,
        actor_user_id=user.id,
        action="MFA_ENABLED",
        entity_type="user",
        entity_id=user.id,
        details={},
    )
    db.commit()


def disable(
    db: Session,
    *,
    user: User,
    password: str,
    code: str,
    current_session_id: uuid.UUID,
    settings: Settings,
) -> int:
    if not verify_password(password, user.password_hash):
        raise errors.bad_request("The password is incorrect.", "CURRENT_PASSWORD_INVALID")
    if not user.mfa_secret_ciphertext:
        user.mfa_enabled = False
        db.commit()
        return 0
    try:
        secret = decrypt_mfa_secret(user.mfa_secret_ciphertext, settings)
    except MfaCryptoError:
        raise errors.conflict("The MFA secret is unreadable.", "MFA_STATE_INVALID")
    if not verify_totp(secret, code):
        audit_service.security(
            db,
            event_type="MFA_DISABLE_FAILED",
            severity=SecuritySeverity.MEDIUM,
            user_id=user.id,
        )
        db.commit()
        raise errors.bad_request("Incorrect authenticator code.", "MFA_CODE_INVALID")
    user.mfa_enabled = False
    user.mfa_secret_ciphertext = None
    user.mfa_enrolled_at = None
    revoked = auth_service.revoke_all_sessions(
        db, user.id, except_session_id=current_session_id
    )
    audit_service.audit(
        db,
        actor_user_id=user.id,
        action="MFA_DISABLED",
        entity_type="user",
        entity_id=user.id,
        details={"other_sessions_revoked": revoked},
    )
    db.commit()
    return revoked


def status(user: User) -> dict:
    return {
        "enabled": bool(user.mfa_enabled),
        "enrolled_at": user.mfa_enrolled_at,
        "pending_setup": bool(user.mfa_secret_ciphertext and not user.mfa_enabled),
    }


def require_code(db: Session, *, user: User, code: str, settings: Settings) -> None:
    """Verify a TOTP code for an already-authenticated user (e.g. password change)."""
    if not user.mfa_enabled or not user.mfa_secret_ciphertext:
        raise errors.bad_request("MFA is not enabled for this account.", "MFA_NOT_ENABLED")
    try:
        secret = decrypt_mfa_secret(user.mfa_secret_ciphertext, settings)
    except MfaCryptoError:
        raise errors.conflict("The MFA secret is unreadable.", "MFA_STATE_INVALID")
    if not verify_totp(secret, code):
        audit_service.security(
            db,
            event_type="MFA_CODE_REJECTED",
            severity=SecuritySeverity.LOW,
            user_id=user.id,
        )
        db.commit()
        raise errors.bad_request("Incorrect authenticator code.", "MFA_CODE_INVALID")


def clear_for_recovery(db: Session, *, user: User, actor_user_id: uuid.UUID) -> None:
    """Administrator recovery action: remove MFA and revoke all sessions."""
    user.mfa_enabled = False
    user.mfa_secret_ciphertext = None
    user.mfa_enrolled_at = None
    revoked = auth_service.revoke_all_sessions(db, user.id)
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="MFA_DISABLED_BY_ADMIN",
        entity_type="user",
        entity_id=user.id,
        details={"sessions_revoked": revoked},
    )
    db.commit()

