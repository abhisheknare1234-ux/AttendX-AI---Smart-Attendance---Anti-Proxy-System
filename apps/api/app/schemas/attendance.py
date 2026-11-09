"""Attendance session, verification flow, review and reporting schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import (
    AttendanceClassification,
    AttendanceStatus,
    AttemptStatus,
    DecisionSource,
    FactorStatus,
    GpsStatus,
    ReviewStatus,
    RiskDecision,
    SessionStatus,
)

RequiredFactorKey = Literal["pin", "gps", "face", "liveness"]


class SessionCreateRequest(BaseModel):
    class_id: uuid.UUID
    subject_id: uuid.UUID
    classroom_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime | None = None
    window_seconds: int | None = Field(default=None, ge=30, le=7200)
    qr_refresh_seconds: int | None = Field(default=None, ge=5, le=600)
    policy_id: uuid.UUID | None = None
    geofence_id: uuid.UUID | None = None
    require_pin: bool | None = None
    require_geofence: bool | None = None
    require_face: bool | None = None
    require_liveness: bool | None = None

    @model_validator(mode="after")
    def _window(self) -> "SessionCreateRequest":
        if self.ends_at is not None and self.starts_at is not None:
            if self.ends_at <= self.starts_at:
                raise ValueError("ends_at must be after starts_at")
            span = (self.ends_at - self.starts_at).total_seconds()
            if span > 4 * 3600:
                raise ValueError("A session may not be longer than 4 hours")
        return self


class QrOut(BaseModel):
    token: str
    url: str
    issued_at: datetime
    expires_at: datetime
    refresh_seconds: int
    session_id: uuid.UUID


class SessionOut(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    class_code: str
    class_name: str
    subject_id: uuid.UUID
    subject_code: str
    subject_name: str
    classroom_id: uuid.UUID
    classroom_name: str
    teacher_id: uuid.UUID
    teacher_name: str
    status: SessionStatus
    starts_at: datetime
    ends_at: datetime
    window_seconds: int
    qr_refresh_seconds: int
    qr_grace_seconds: int
    require_pin: bool
    require_geofence: bool
    require_face: bool
    require_liveness: bool
    allow_review_outside_geofence: bool
    pin_available: bool
    opened_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    eligible_students: int = 0
    accepted: int = 0
    pending: int = 0
    rejected: int = 0
    review_required: int = 0


class OpenSessionResponse(BaseModel):
    session: SessionOut
    pin: str | None
    pin_expires_at: datetime | None
    qr: QrOut


class LiveAttemptOut(BaseModel):
    attempt_id: uuid.UUID
    reference: str
    student_name: str
    roll_number: str
    status: AttemptStatus
    current_step: str
    gps_status: GpsStatus
    face_status: FactorStatus
    liveness_status: FactorStatus
    risk_decision: RiskDecision | None
    created_at: datetime


class LiveSessionResponse(BaseModel):
    session: SessionOut
    qr: QrOut | None
    seconds_remaining: int
    recent_attempts: list[LiveAttemptOut]


class QrValidateRequest(BaseModel):
    token: str = Field(min_length=10, max_length=2048)


class RequirementsOut(BaseModel):
    pin: bool
    geofence: bool
    face: bool
    liveness: bool


class QrValidateResponse(BaseModel):
    session_id: uuid.UUID
    class_name: str
    subject_name: str
    classroom_name: str
    teacher_name: str
    status: SessionStatus
    starts_at: datetime
    ends_at: datetime
    seconds_remaining: int
    requirements: RequirementsOut
    already_recorded: bool
    existing_status: AttendanceStatus | None = None
    can_check_in: bool
    message: str


class CheckInRequest(BaseModel):
    qr_token: str = Field(min_length=10, max_length=2048)


class AttemptOut(BaseModel):
    id: uuid.UUID
    reference: str
    session_id: uuid.UUID
    status: AttemptStatus
    current_step: str
    qr_status: FactorStatus
    pin_status: FactorStatus
    gps_status: GpsStatus
    face_status: FactorStatus
    liveness_status: FactorStatus
    pin_attempts: int
    gps_distance_m: float | None
    gps_accuracy_m: float | None
    risk_score: int
    risk_decision: RiskDecision | None
    risk_reasons: list[dict] | None
    created_at: datetime
    completed_at: datetime | None


class CheckInResponse(BaseModel):
    attempt: AttemptOut
    session: QrValidateResponse
    required_steps: list[RequiredFactorKey]
    next_step: RequiredFactorKey | None


class PinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=10, pattern=r"^\d+$")


class StepResponse(BaseModel):
    attempt: AttemptOut
    next_step: RequiredFactorKey | None
    message: str


class FactorStepResponse(StepResponse):
    factor: str
    status: FactorStatus
    reason_code: str | None = None
    provider: str | None = None
    score: float | None = None


class AttemptDetailResponse(BaseModel):
    attempt: AttemptOut
    session: QrValidateResponse
    next_step: RequiredFactorKey | None


class LocationRequest(BaseModel):
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_m: float | None = Field(default=None, ge=0, le=100000)
    client_timestamp: str | None = Field(default=None, max_length=64)
    permission_denied: bool = False
    unavailable: bool = False

    @model_validator(mode="after")
    def _coords(self) -> "LocationRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        return self


class LocationStepResponse(StepResponse):
    gps_status: GpsStatus
    distance_m: float | None
    accuracy_m: float | None
    reason_code: str | None


class FinalizeResponse(BaseModel):
    record_id: uuid.UUID
    reference: str
    session_id: uuid.UUID
    status: AttendanceStatus
    classification: AttendanceClassification
    decision_source: DecisionSource
    decision: RiskDecision
    risk_score: int
    reasons: list[dict]
    check_in_at: datetime | None


class AttendanceHistoryItem(BaseModel):
    record_id: uuid.UUID
    reference: str
    session_id: uuid.UUID
    subject_name: str
    subject_code: str
    class_name: str
    status: AttendanceStatus
    classification: AttendanceClassification
    decision_source: DecisionSource
    check_in_at: datetime | None
    session_starts_at: datetime
    session_ends_at: datetime


class SubjectAttendanceSummary(BaseModel):
    subject_id: uuid.UUID
    subject_name: str
    subject_code: str
    class_name: str
    sessions: int
    present: int
    percentage: float | None


class ActiveSessionSummary(BaseModel):
    session_id: uuid.UUID
    subject_name: str
    class_name: str
    status: SessionStatus
    ends_at: datetime
    seconds_remaining: int


class StudentDashboardResponse(BaseModel):
    student_name: str
    roll_number: str
    total_sessions: int
    attended_sessions: int
    attendance_percentage: float | None
    pending_reviews: int
    active_sessions: list[ActiveSessionSummary]
    upcoming_sessions: list[ActiveSessionSummary]
    subjects: list[SubjectAttendanceSummary]
    recent_records: list[AttendanceHistoryItem]


class ReviewCreateRequest(BaseModel):
    session_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=500)


class ReviewOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    subject_name: str
    class_name: str
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    reason: str
    status: ReviewStatus
    attempt_reference: str | None = None
    record_reference: str | None = None
    risk_decision: RiskDecision | None = None
    risk_score: int | None = None
    risk_reasons: list[dict] | None = None
    session_starts_at: datetime
    created_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None


class ResolveReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(min_length=3, max_length=1000)
    mark_present: bool | None = None


class CorrectionRequest(BaseModel):
    new_status: AttendanceStatus
    new_classification: AttendanceClassification | None = None
    reason: str = Field(min_length=5, max_length=500)


class TeacherDashboardResponse(BaseModel):
    teacher_name: str
    classes_count: int
    subjects_count: int
    students_count: int
    active_sessions: int
    today_sessions: int
    present_today: int
    review_pending: int
    failed_attempts_today: int
    recent_sessions: list[SessionOut]
    review_queue: list[ReviewOut]


class ReportRowOut(BaseModel):
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    class_name: str
    subject_name: str
    sessions_held: int
    sessions_present: int
    attendance_percentage: float | None


class AttendanceReportResponse(BaseModel):
    generated_at: datetime
    filters: dict
    totals: dict
    rows: list[ReportRowOut]
