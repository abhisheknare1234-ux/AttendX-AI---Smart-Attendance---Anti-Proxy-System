"""Audit and security event recording helpers (caller commits)."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, SecurityEvent, SecuritySeverity


def audit(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: str | uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ip_address: str | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or {},
        ip_address=ip_address,
    )
    db.add(event)
    return event


def security(
    db: Session,
    *,
    event_type: str,
    severity: SecuritySeverity = SecuritySeverity.INFO,
    user_id: uuid.UUID | None = None,
    session_id: uuid.UUID | None = None,
    ip_address: str | None = None,
    details: dict[str, Any] | None = None,
) -> SecurityEvent:
    event = SecurityEvent(
        event_type=event_type,
        severity=severity,
        user_id=user_id,
        session_id=session_id,
        ip_address=ip_address,
        details=details or {},
    )
    db.add(event)
    return event
