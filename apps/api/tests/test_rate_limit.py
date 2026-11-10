"""Database-backed, cross-session rate limiting tests."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from app.core.rate_limit import check_rate_limit, clear_rate_limit
from app.core.timeutil import utcnow
from app.models import RateLimitCounter
from tests.conftest import TestingSessionLocal


def test_shared_counter_enforced_across_sessions(seeded, db):
    key = "test:shared-counter"
    clear_rate_limit(db, key)

    first, _ = check_rate_limit(db, key=key, limit=2, window_seconds=300)
    assert first is True
    with TestingSessionLocal() as other:
        second, _ = check_rate_limit(other, key=key, limit=2, window_seconds=300)
        assert second is True
        third, retry = check_rate_limit(other, key=key, limit=2, window_seconds=300)
        assert third is False
        assert retry > 0

    row = db.scalar(select(RateLimitCounter).where(RateLimitCounter.key == key))
    assert row is not None and row.count == 2


def test_window_resets(seeded, db):
    key = "test:reset-window"
    clear_rate_limit(db, key)
    assert check_rate_limit(db, key=key, limit=1, window_seconds=60)[0] is True
    assert check_rate_limit(db, key=key, limit=1, window_seconds=60)[0] is False
    row = db.scalar(select(RateLimitCounter).where(RateLimitCounter.key == key))
    row.window_start = utcnow() - timedelta(seconds=61)
    db.commit()
    assert check_rate_limit(db, key=key, limit=1, window_seconds=60)[0] is True


def test_keys_are_isolated(seeded, db):
    clear_rate_limit(db, "test:a")
    clear_rate_limit(db, "test:b")
    assert check_rate_limit(db, key="test:a", limit=1, window_seconds=60)[0] is True
    assert check_rate_limit(db, key="test:a", limit=1, window_seconds=60)[0] is False
    assert check_rate_limit(db, key="test:b", limit=1, window_seconds=60)[0] is True
