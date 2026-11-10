"""Retention cleanup for transient authentication and verification data.

Attendance records and audit/security evidence are deliberately **not** deleted
here; institutional retention policy and legal obligations govern those. This
job removes expired sessions/challenges/tokens, stale rate-limit counters and
old verification evidence (which may contain location details). Run dry-run
first; `--apply` performs and audits the deletion.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.timeutil import utcnow
from app.models import (
    AuthSession,
    MfaChallenge,
    PasswordResetToken,
    RateLimitCounter,
    VerificationEvidence,
)
from app.services import audit as audit_service

TOKEN_RETENTION_DAYS = 7
RATE_LIMIT_RETENTION_HOURS = 24


def _count(db: Session, model, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def cleanup(db: Session, *, settings: Settings, apply: bool = False) -> dict[str, int]:
    now = utcnow()
    evidence_cutoff = now - timedelta(days=settings.evidence_retention_days)
    session_cutoff = now - timedelta(days=settings.session_retention_days)
    token_cutoff = now - timedelta(days=TOKEN_RETENTION_DAYS)
    rate_cutoff = now - timedelta(hours=RATE_LIMIT_RETENTION_HOURS)

    session_filter = (
        AuthSession.created_at < session_cutoff,
        or_(AuthSession.expires_at < now, AuthSession.revoked_at.is_not(None)),
    )
    challenge_filter = (
        MfaChallenge.created_at < token_cutoff,
        or_(MfaChallenge.expires_at < now, MfaChallenge.consumed_at.is_not(None)),
    )
    reset_filter = (
        PasswordResetToken.created_at < token_cutoff,
        or_(
            PasswordResetToken.expires_at < now,
            PasswordResetToken.used_at.is_not(None),
        ),
    )
    evidence_filter = (VerificationEvidence.created_at < evidence_cutoff,)
    rate_filter = (RateLimitCounter.updated_at < rate_cutoff,)

    counts = {
        "auth_sessions": _count(db, AuthSession, *session_filter),
        "mfa_challenges": _count(db, MfaChallenge, *challenge_filter),
        "password_reset_tokens": _count(db, PasswordResetToken, *reset_filter),
        "verification_evidence": _count(db, VerificationEvidence, *evidence_filter),
        "rate_limit_counters": _count(db, RateLimitCounter, *rate_filter),
    }
    if not apply:
        return counts

    db.execute(delete(AuthSession).where(*session_filter))
    db.execute(delete(MfaChallenge).where(*challenge_filter))
    db.execute(delete(PasswordResetToken).where(*reset_filter))
    db.execute(delete(VerificationEvidence).where(*evidence_filter))
    db.execute(delete(RateLimitCounter).where(*rate_filter))
    audit_service.audit(
        db,
        actor_user_id=None,
        action="RETENTION_CLEANUP",
        entity_type="system",
        details={
            "counts": counts,
            "evidence_retention_days": settings.evidence_retention_days,
            "session_retention_days": settings.session_retention_days,
        },
    )
    db.commit()
    return counts
