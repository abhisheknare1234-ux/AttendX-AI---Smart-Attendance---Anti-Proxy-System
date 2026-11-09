"""Academic configuration: terms, classes, subjects, classrooms, enrolments,
teacher assignments, geofences and attendance policies."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, enum_column, utcnow, uuid_pk
from app.models.enums import EnrollmentStatus


class AcademicTerm(Base):
    __tablename__ = "academic_terms"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(80), unique=True)
    start_date: Mapped[datetime] = mapped_column()
    end_date: Mapped[datetime] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class SchoolClass(Base):
    __tablename__ = "classes"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    department: Mapped[str] = mapped_column(String(120))
    year: Mapped[int] = mapped_column(default=1)
    division: Mapped[str] = mapped_column(String(10), default="A")
    academic_term_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("academic_terms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Subject(Base):
    __tablename__ = "subjects"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True
    )
    credits: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class Classroom(Base):
    __tablename__ = "classrooms"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    building: Mapped[str | None] = mapped_column(String(120), nullable=True)
    floor: Mapped[str | None] = mapped_column(String(20), nullable=True)
    latitude: Mapped[float] = mapped_column()
    longitude: Mapped[float] = mapped_column()
    default_radius_m: Mapped[float] = mapped_column(default=60.0)
    max_accuracy_m: Mapped[float] = mapped_column(default=100.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class ClassEnrollment(Base):
    __tablename__ = "class_enrollments"
    __table_args__ = (
        UniqueConstraint("class_id", "student_id", name="uq_class_enrollments_class_student"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("student_profiles.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[EnrollmentStatus] = enum_column(EnrollmentStatus, default=EnrollmentStatus.ACTIVE)
    enrolled_at: Mapped[datetime] = mapped_column(default=utcnow)


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"
    __table_args__ = (
        UniqueConstraint(
            "teacher_id", "class_id", "subject_id", name="uq_teacher_assignments_scope"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    teacher_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("teacher_profiles.id", ondelete="CASCADE"), index=True
    )
    class_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), index=True
    )
    subject_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    assigned_at: Mapped[datetime] = mapped_column(default=utcnow)


class GeofencePolicy(Base):
    __tablename__ = "geofence_policies"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True)
    classroom_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True, index=True
    )
    center_latitude: Mapped[float] = mapped_column()
    center_longitude: Mapped[float] = mapped_column()
    radius_m: Mapped[float] = mapped_column(default=60.0)
    max_accuracy_m: Mapped[float] = mapped_column(default=100.0)
    allow_review_outside: Mapped[bool] = mapped_column(default=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)


class AttendancePolicy(Base):
    __tablename__ = "attendance_policies"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120), unique=True)
    is_default: Mapped[bool] = mapped_column(default=False)
    attendance_window_seconds: Mapped[int] = mapped_column(default=180)
    qr_refresh_seconds: Mapped[int] = mapped_column(default=30)
    qr_grace_seconds: Mapped[int] = mapped_column(default=15)
    require_pin: Mapped[bool] = mapped_column(default=True)
    require_geofence: Mapped[bool] = mapped_column(default=True)
    require_face: Mapped[bool] = mapped_column(default=False)
    require_liveness: Mapped[bool] = mapped_column(default=False)
    allow_review_outside_geofence: Mapped[bool] = mapped_column(default=True)
    presence_monitoring_enabled: Mapped[bool] = mapped_column(default=False)
    full_presence_ratio: Mapped[float] = mapped_column(default=0.8)
    partial_presence_ratio: Mapped[float] = mapped_column(default=0.5)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
