"""Operations, review, biometric enrolment and configuration models."""
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
    BiometricStatus,
    ImportStatus,
    ReviewStatus,
    SecuritySeverity,
)


class AuditEvent(Base):
    """Append-only administrative audit trail."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[SecuritySeverity] = enum_column(
        SecuritySeverity, default=SecuritySeverity.INFO, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[uuid.UUID] = uuid_pk()
    record_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attendance_records.id", ondelete="CASCADE"), nullable=True, index=True
    )
    attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attendance_attempts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[ReviewStatus] = enum_column(ReviewStatus, default=ReviewStatus.OPEN, index=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id: Mapped[uuid.UUID] = uuid_pk()
    record_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("attendance_records.id", ondelete="CASCADE"), index=True
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    old_status: Mapped[AttendanceStatus] = enum_column(AttendanceStatus)
    new_status: Mapped[AttendanceStatus] = enum_column(AttendanceStatus)
    old_classification: Mapped[AttendanceClassification | None] = enum_column(
        AttendanceClassification, nullable=True
    )
    new_classification: Mapped[AttendanceClassification | None] = enum_column(
        AttendanceClassification, nullable=True
    )
    reason: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class BiometricEnrollment(Base):
    """Metadata only. This build stores no raw biometric images or templates."""

    __tablename__ = "biometric_enrollments"

    id: Mapped[uuid.UUID] = uuid_pk()
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), unique=True, index=True
    )
    provider: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str] = mapped_column(String(64))
    status: Mapped[BiometricStatus] = enum_column(
        BiometricStatus, default=BiometricStatus.NOT_ENROLLED
    )
    template_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    template_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_dimension: Mapped[int | None] = mapped_column(nullable=True)
    consent_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    consented_at: Mapped[datetime | None] = mapped_column(nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class ImportJob(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    kind: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ImportStatus] = enum_column(ImportStatus, default=ImportStatus.PREVIEWED)
    total_rows: Mapped[int] = mapped_column(default=0)
    success_rows: Mapped[int] = mapped_column(default=0)
    error_rows: Mapped[int] = mapped_column(default=0)
    errors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
