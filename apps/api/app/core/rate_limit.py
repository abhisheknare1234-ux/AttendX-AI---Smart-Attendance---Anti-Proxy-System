"""Database-backed fixed-window rate limiting.

The counter row is shared by every API process, so a multi-worker deployment
enforces one limit instead of one per worker. Fixed windows are simple and
sufficient for login/PIN abuse protection; they are not a general traffic
shaper. Denied attempts do not reset or extend the window.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.timeutil import utcnow
from app.models import RateLimitCounter


def check_rate_limit(
    db: Session, *, key: str, limit: int, window_seconds: int
) -> tuple[bool, int]:
    """Record one attempt and return (allowed, retry_after_seconds)."""
    if limit <= 0:
        return False, window_seconds
    now = utcnow()
    row = db.scalar(
        select(RateLimitCounter).where(RateLimitCounter.key == key).with_for_update()
    )
    if row is None:
        row = RateLimitCounter(key=key, window_start=now, count=1)
        db.add(row)
        try:
            db.commit()
            return True, 0
        except IntegrityError:
            db.rollback()
            # Another worker created it first; retry once through the update path.
            row = db.scalar(
                select(RateLimitCounter)
                .where(RateLimitCounter.key == key)
                .with_for_update()
            )
            if row is None:
                return False, window_seconds

    window_end = row.window_start + timedelta(seconds=window_seconds)
    if window_end <= now:
        row.window_start = now
        row.count = 1
        row.updated_at = now
        db.commit()
        return True, 0
    if row.count >= limit:
        retry_after = max(1, int((window_end - now).total_seconds()) + 1)
        db.rollback()
        return False, retry_after
    row.count += 1
    row.updated_at = now
    db.commit()
    return True, 0


def clear_rate_limit(db: Session, key: str) -> None:
    row = db.scalar(select(RateLimitCounter).where(RateLimitCounter.key == key))
    if row is not None:
        db.delete(row)
        db.commit()
