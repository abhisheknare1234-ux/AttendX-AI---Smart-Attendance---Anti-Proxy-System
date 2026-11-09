"""Attendance session, QR token, attempt, evidence and record models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import Base, enum_column, utcnow, uuid_pk
from app.models.enums import (
    AttendanceClassification,
    AttendanceStatus,
    AttemptStatus,
    DecisionSource,
    FactorStatus,
    GpsStatus,
    PresenceEventType,
    RiskDecision,
    SessionStatus,
)


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="RESTRICT"), index=True
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), index=True
    )
    classroom_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classrooms.id", ondelete="RESTRICT"), index=True
    )
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teacher_profiles.id", ondelete="RESTRICT"), index=True
    )
    policy_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attendance_policies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    geofence_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("geofence_policies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[SessionStatus] = enum_column(
        SessionStatus, default=SessionStatus.SCHEDULED, index=True
    )
    starts_at: Mapped[datetime] = mapped_column()
    ends_at: Mapped[datetime] = mapped_column()
    window_seconds: Mapped[int] = mapped_column(default=180)
    qr_refresh_seconds: Mapped[int] = mapped_column(default=30)
    qr_grace_seconds: Mapped[int] = mapped_column(default=15)
    require_pin: Mapped[bool] = mapped_column(default=True)
    require_geofence: Mapped[bool] = mapped_column(default=True)
    require_face: Mapped[bool] = mapped_column(default=False)
    require_liveness: Mapped[bool] = mapped_column(default=False)
    allow_review_outside_geofence: Mapped[bool] = mapped_column(default=True)
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pin_expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class QrToken(Base):
    """A rotated QR token. The signed token string itself is never stored."""

    __tablename__ = "qr_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    nonce: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    issued_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(index=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    revoked_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AttendanceAttempt(Base):
    __tablename__ = "attendance_attempts"

    id: Mapped[uuid.UUID] = uuid_pk()
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), index=True
    )
    qr_token_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("qr_tokens.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[AttemptStatus] = enum_column(
        AttemptStatus, default=AttemptStatus.IN_PROGRESS, index=True
    )
    current_step: Mapped[str] = mapped_column(String(32), default="pin")
    qr_status: Mapped[FactorStatus] = enum_column(FactorStatus, default=FactorStatus.PENDING)
    pin_status: Mapped[FactorStatus] = enum_column(FactorStatus, default=FactorStatus.PENDING)
    gps_status: Mapped[GpsStatus] = enum_column(GpsStatus, default=GpsStatus.UNAVAILABLE)
    face_status: Mapped[FactorStatus] = enum_column(FactorStatus, default=FactorStatus.PENDING)
    liveness_status: Mapped[FactorStatus] = enum_column(
        FactorStatus, default=FactorStatus.PENDING
    )
    pin_attempts: Mapped[int] = mapped_column(default=0)
    gps_distance_m: Mapped[float | None] = mapped_column(nullable=True)
    gps_accuracy_m: Mapped[float | None] = mapped_column(nullable=True)
    gps_recorded_at: Mapped[datetime | None] = mapped_column(nullable=True)
    gps_submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    risk_score: Mapped[int] = mapped_column(default=0)
    risk_decision: Mapped[RiskDecision | None] = enum_column(
        RiskDecision, nullable=True
    )
    risk_reasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    client_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class VerificationEvidence(Base):
    __tablename__ = "verification_evidence"

    id: Mapped[uuid.UUID] = uuid_pk()
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_attempts.id", ondelete="CASCADE"), index=True
    )
    factor: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    score: Mapped[float | None] = mapped_column(nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("session_id", "student_id", name="uq_attendance_records_session_student"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    reference: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="RESTRICT"), index=True
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attendance_attempts.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    status: Mapped[AttendanceStatus] = enum_column(AttendanceStatus, index=True)
    classification: Mapped[AttendanceClassification] = enum_column(
        AttendanceClassification, default=AttendanceClassification.PENDING_REVIEW
    )
    decision_source: Mapped[DecisionSource] = enum_column(DecisionSource, default=DecisionSource.SYSTEM)
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    decided_at: Mapped[datetime] = mapped_column(default=utcnow)
    check_in_at: Mapped[datetime | None] = mapped_column(nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class PresenceEvent(Base):
    """Optional in-lecture presence signal (BLE/proximity). Schema only in this build."""

    __tablename__ = "presence_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[PresenceEventType] = enum_column(PresenceEventType)
    source: Mapped[str] = mapped_column(String(32), default="ble")
    occurred_at: Mapped[datetime] = mapped_column(default=utcnow)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
