"""Retention cleanup tests with dry-run and apply semantics."""
from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import select

from app.models import (
    AuditEvent,
    MfaChallenge,
    PasswordResetToken,
    RateLimitCounter,
)
from app.core.timeutil import utcnow
from app.services.retention import cleanup


def test_retention_dry_run_then_apply(seeded, db, settings):
    old = utcnow() - timedelta(days=400)
    student_user_id = uuid.UUID(seeded["student_user_id"])
    db.add(
        RateLimitCounter(
            key="retention:stale", window_start=old, count=3, updated_at=old
        )
    )
    db.add(
        MfaChallenge(
            user_id=student_user_id,
            token_hash="a" * 64,
            attempts=1,
            expires_at=old,
            created_at=old,
        )
    )
    db.add(
        PasswordResetToken(
            user_id=student_user_id,
            token_hash="b" * 64,
            expires_at=old,
            used_at=old,
            created_at=old,
        )
    )
    db.commit()

    counts = cleanup(db, settings=settings, apply=False)
    assert counts["rate_limit_counters"] >= 1
    assert counts["mfa_challenges"] >= 1
    assert counts["password_reset_tokens"] >= 1
    assert db.scalar(select(RateLimitCounter).where(RateLimitCounter.key == "retention:stale"))

    applied = cleanup(db, settings=settings, apply=True)
    assert applied["rate_limit_counters"] >= 1
    assert db.scalar(select(RateLimitCounter).where(RateLimitCounter.key == "retention:stale")) is None
    assert db.scalar(
        select(AuditEvent).where(AuditEvent.action == "RETENTION_CLEANUP")
    ) is not None
