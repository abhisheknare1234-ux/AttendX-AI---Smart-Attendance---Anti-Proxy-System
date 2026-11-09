"""Shared enumerations.

Values are stored as plain strings (no native database enums) so migrations
remain simple and portable between PostgreSQL and the SQLite dev profile.
"""
from __future__ import annotations

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
    LOCKED = "locked"


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVIEW_REQUIRED = "review_required"
    EXPIRED = "expired"
    ABANDONED = "abandoned"


class FactorStatus(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_REQUIRED = "NOT_REQUIRED"
    PENDING_REVIEW = "PENDING_REVIEW"
    PENDING = "PENDING"
    NOT_SUBMITTED = "NOT_SUBMITTED"


class GpsStatus(StrEnum):
    INSIDE_GEOFENCE = "INSIDE_GEOFENCE"
    OUTSIDE_GEOFENCE = "OUTSIDE_GEOFENCE"
    LOW_ACCURACY = "LOW_ACCURACY"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class RiskDecision(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    ABSENT = "absent"
    REVIEW_REQUIRED = "review_required"
    REJECTED = "rejected"


class AttendanceClassification(StrEnum):
    FULL = "FULL"
    PARTIAL = "PARTIAL"
    INTERRUPTED = "INTERRUPTED"
    INVALID = "INVALID"
    ABSENT = "ABSENT"
    PENDING_REVIEW = "PENDING_REVIEW"


class DecisionSource(StrEnum):
    SYSTEM = "system"
    TEACHER = "teacher"


class ReviewStatus(StrEnum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class EnrollmentStatus(StrEnum):
    ACTIVE = "active"
    DROPPED = "dropped"


class BiometricStatus(StrEnum):
    NOT_ENROLLED = "not_enrolled"
    PENDING = "pending"
    ACTIVE = "active"
    DELETED = "deleted"


class Purpose(StrEnum):
    """What a biometric template is authorized for."""

    FACE_VERIFICATION = "face_verification"


class SecuritySeverity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ImportStatus(StrEnum):
    PREVIEWED = "previewed"
    COMMITTED = "committed"
    FAILED = "failed"


class PresenceEventType(StrEnum):
    CHECK_IN = "check_in"
    PROXIMITY_SEEN = "proximity_seen"
    PROXIMITY_LOST = "proximity_lost"
    LECTURE_END = "lecture_end"
