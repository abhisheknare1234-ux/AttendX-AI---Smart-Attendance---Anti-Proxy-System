"""Administrator-issued, single-use password reset tokens.

Email delivery is not configured, so an administrator generates a one-time token
and hands the reset URL to the user through an approved channel. Tokens are
hashed at rest, expire, are single-use, and revoke all existing sessions when
redeemed.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings
from app.core.rate_limit import check_rate_limit
from app.core.security import generate_token, hash_password, password_problem, token_hash
from app.core.timeutil import utcnow
from app.models import PasswordResetToken, SecuritySeverity, User, UserStatus
from app.services import audit as audit_service
from app.services import auth as auth_service


def issue_token(
    db: Session,
    *,
    user: User,
    actor_user_id: uuid.UUID,
    settings: Settings,
) -> tuple[str, PasswordResetToken]:
    now = utcnow()
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    raw_token = generate_token(32)
    row = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        created_by_id=actor_user_id,
        expires_at=now + timedelta(minutes=settings.password_reset_ttl_minutes),
    )
    db.add(row)
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="PASSWORD_RESET_ISSUED",
        entity_type="user",
        entity_id=user.id,
        details={"expires_at": row.expires_at.isoformat()},
    )
    db.commit()
    db.refresh(row)
    return raw_token, row


def reset_password(
    db: Session,
    *,
    raw_token: str,
    new_password: str,
    settings: Settings,
    ip_address: str | None = None,
) -> User:
    allowed, retry_after = check_rate_limit(
        db,
        key=f"password-reset:ip:{ip_address or 'unknown'}",
        limit=10,
        window_seconds=300,
    )
    if not allowed:
        raise errors.too_many_requests("Too many password reset attempts.", retry_after)
    problem = password_problem(new_password)
    if problem:
        raise errors.bad_request(problem, "WEAK_PASSWORD")

    row = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash(raw_token))
    )
    now = utcnow()
    if row is None or row.used_at is not None or row.expires_at <= now:
        raise errors.bad_request(
            "This password reset link is invalid or has expired. Request a new one.",
            "PASSWORD_RESET_INVALID",
        )
    user = db.get(User, row.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise errors.bad_request(
            "This password reset link cannot be used for this account.",
            "PASSWORD_RESET_INVALID",
        )
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    row.used_at = now
    revoked = auth_service.revoke_all_sessions(db, user.id)
    audit_service.security(
        db,
        event_type="PASSWORD_RESET_COMPLETED",
        severity=SecuritySeverity.HIGH,
        user_id=user.id,
        ip_address=ip_address,
        details={"sessions_revoked": revoked},
    )
    audit_service.audit(
        db,
        actor_user_id=user.id,
        action="PASSWORD_RESET_COMPLETED",
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
        details={"sessions_revoked": revoked},
    )
    db.commit()
    return user
