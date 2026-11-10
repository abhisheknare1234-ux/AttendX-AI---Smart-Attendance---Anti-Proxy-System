"""Authentication service: Argon2id verification, lockout, server sessions, MFA gate."""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings
from app.core.rate_limit import check_rate_limit
from app.core.security import (
    generate_token,
    hash_password,
    password_problem,
    token_hash,
    verify_password,
)
from app.core.timeutil import utcnow
from app.models import AuthSession, SecuritySeverity, User, UserRole, UserStatus
from app.services import audit as audit_service

# A valid Argon2id hash used to keep response time similar for unknown emails.
_DUMMY_HASH = hash_password("attendx-timing-equalisation-value")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def _check_login_rate(db: Session, email: str, ip: str | None, settings: Settings) -> None:
    email_allowed, email_retry = check_rate_limit(
        db,
        key=f"login:email:{email}",
        limit=settings.login_max_attempts * 2,
        window_seconds=settings.login_window_seconds,
    )
    ip_allowed, ip_retry = check_rate_limit(
        db,
        key=f"login:ip:{ip or 'unknown'}",
        limit=settings.ip_rate_limit_per_minute * 4,
        window_seconds=settings.login_window_seconds,
    )
    if not email_allowed or not ip_allowed:
        raise errors.too_many_requests(
            "Too many sign-in attempts. Please wait and try again.",
            retry_after=max(email_retry, ip_retry),
        )


def verify_credentials(
    db: Session,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    settings: Settings,
) -> User:
    """Validate email/password/lockout. Does not create a session or complete MFA."""
    email = normalize_email(email)
    _check_login_rate(db, email, ip_address, settings)
    now = utcnow()

    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        audit_service.security(
            db,
            event_type="LOGIN_FAILED_UNKNOWN_EMAIL",
            severity=SecuritySeverity.LOW,
            ip_address=ip_address,
            details={"email_domain": email.rsplit("@", 1)[-1]},
        )
        db.commit()
        raise errors.unauthorized("Invalid email or password.")

    if user.locked_until is not None and user.locked_until > now:
        audit_service.security(
            db,
            event_type="LOGIN_BLOCKED_LOCKED_ACCOUNT",
            severity=SecuritySeverity.MEDIUM,
            user_id=user.id,
            ip_address=ip_address,
        )
        db.commit()
        raise errors.unauthorized("Invalid email or password.")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.login_max_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_login_count = 0
            audit_service.security(
                db,
                event_type="ACCOUNT_LOCKED",
                severity=SecuritySeverity.HIGH,
                user_id=user.id,
                ip_address=ip_address,
            )
        audit_service.security(
            db,
            event_type="LOGIN_FAILED",
            severity=SecuritySeverity.LOW,
            user_id=user.id,
            ip_address=ip_address,
        )
        db.commit()
        raise errors.unauthorized("Invalid email or password.")

    if user.status != UserStatus.ACTIVE:
        audit_service.security(
            db,
            event_type="LOGIN_BLOCKED_INACTIVE",
            severity=SecuritySeverity.MEDIUM,
            user_id=user.id,
            ip_address=ip_address,
        )
        db.commit()
        raise errors.forbidden("This account is not active. Contact your administrator.")

    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    return user


def start_session(
    db: Session,
    *,
    user: User,
    ip_address: str | None,
    user_agent: str | None,
    settings: Settings,
    event_type: str = "LOGIN_SUCCEEDED",
) -> tuple[AuthSession, str]:
    now = utcnow()
    user.last_login_at = now
    raw_token = generate_token(48)
    session = AuthSession(
        user_id=user.id,
        token_hash=token_hash(raw_token),
        csrf_token=generate_token(32),
        ip_address=ip_address,
        user_agent=(user_agent or "")[:300] or None,
        expires_at=now + timedelta(minutes=settings.session_ttl_minutes),
        last_seen_at=now,
    )
    db.add(session)
    audit_service.audit(
        db,
        actor_user_id=user.id,
        action="AUTH_LOGIN" if event_type == "LOGIN_SUCCEEDED" else "AUTH_LOGIN_MFA",
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
    )
    audit_service.security(
        db,
        event_type=event_type,
        severity=SecuritySeverity.INFO,
        user_id=user.id,
        ip_address=ip_address,
        details={"mfa": event_type == "LOGIN_SUCCEEDED_MFA"},
    )
    db.commit()
    db.refresh(session)
    return session, raw_token


def authenticate(
    db: Session,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
    settings: Settings,
) -> tuple[User, AuthSession | None, str | None]:
    """Verify credentials; returns no session when a TOTP challenge is required."""
    user = verify_credentials(
        db, email=email, password=password, ip_address=ip_address, settings=settings
    )
    if user.mfa_enabled:
        return user, None, None
    session, raw_token = start_session(
        db,
        user=user,
        ip_address=ip_address,
        user_agent=user_agent,
        settings=settings,
    )
    return user, session, raw_token


def revoke(db: Session, session: AuthSession) -> None:
    if session.revoked_at is None:
        session.revoked_at = utcnow()
        db.commit()


def revoke_all_sessions(
    db: Session, user_id: uuid.UUID, *, except_session_id: uuid.UUID | None = None
) -> int:
    query = (
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    if except_session_id is not None:
        query = query.where(AuthSession.id != except_session_id)
    result = db.execute(query)
    return int(result.rowcount or 0)


def create_user(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str,
    role: UserRole,
    must_change_password: bool = True,
) -> User:
    problem = password_problem(password)
    if problem:
        raise errors.bad_request(problem, "WEAK_PASSWORD")
    email = normalize_email(email)
    if db.scalar(select(User).where(func.lower(User.email) == email)) is not None:
        raise errors.conflict("An account with this email already exists.", "EMAIL_EXISTS")
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip(),
        role=role,
        must_change_password=must_change_password,
    )
    db.add(user)
    return user


def bootstrap_admin(db: Session, *, email: str, password: str, full_name: str) -> User:
    """Create the first administrator idempotently. Never hardcodes a credential."""
    email = normalize_email(email)
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing is not None:
        if existing.role != UserRole.ADMIN:
            raise errors.conflict(
                "An account with this email exists but is not an administrator.",
                "EMAIL_EXISTS",
            )
        return existing
    problem = password_problem(password)
    if problem:
        raise errors.bad_request(problem, "WEAK_PASSWORD")
    user = User(
        email=email,
        password_hash=hash_password(password),
        full_name=full_name.strip() or "Institutional Administrator",
        role=UserRole.ADMIN,
        must_change_password=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
