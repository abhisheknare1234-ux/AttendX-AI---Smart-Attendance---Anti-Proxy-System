"""Academic configuration schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import EnrollmentStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ClassCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=120)
    year: int = Field(default=1, ge=1, le=6)
    division: str = Field(default="A", max_length=10)


class ClassUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    year: int | None = Field(default=None, ge=1, le=6)
    division: str | None = Field(default=None, max_length=10)
    is_active: bool | None = None


class ClassOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    department: str
    year: int
    division: str
    is_active: bool
    created_at: datetime
    enrolled_count: int = 0


class SubjectCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=160)
    class_id: uuid.UUID
    credits: int | None = Field(default=None, ge=0, le=20)


class SubjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    credits: int | None = Field(default=None, ge=0, le=20)
    is_active: bool | None = None


class SubjectOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    class_id: uuid.UUID
    class_code: str | None = None
    class_name: str | None = None
    credits: int | None = None
    is_active: bool


class ClassroomCreateRequest(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    building: str | None = Field(default=None, max_length=120)
    floor: str | None = Field(default=None, max_length=20)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    default_radius_m: float = Field(default=60.0, ge=5, le=1000)
    max_accuracy_m: float = Field(default=100.0, ge=5, le=2000)


class ClassroomUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    building: str | None = Field(default=None, max_length=120)
    floor: str | None = Field(default=None, max_length=20)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    default_radius_m: float | None = Field(default=None, ge=5, le=1000)
    max_accuracy_m: float | None = Field(default=None, ge=5, le=2000)
    is_active: bool | None = None


class ClassroomOut(ORMModel):
    id: uuid.UUID
    code: str
    name: str
    building: str | None
    floor: str | None
    latitude: float
    longitude: float
    default_radius_m: float
    max_accuracy_m: float
    is_active: bool


class EnrollmentCreateRequest(BaseModel):
    class_id: uuid.UUID
    student_ids: list[uuid.UUID] = Field(min_length=1, max_length=500)


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    class_id: uuid.UUID
    class_name: str
    student_id: uuid.UUID
    student_name: str
    roll_number: str
    status: EnrollmentStatus
    enrolled_at: datetime


class EnrollmentBulkResponse(BaseModel):
    created: int
    skipped: int
    enrollments: list[EnrollmentOut]


class AssignmentCreateRequest(BaseModel):
    teacher_id: uuid.UUID
    class_id: uuid.UUID
    subject_id: uuid.UUID | None = None


class AssignmentOut(BaseModel):
    id: uuid.UUID
    teacher_id: uuid.UUID
    teacher_name: str
    class_id: uuid.UUID
    class_name: str
    subject_id: uuid.UUID | None
    subject_name: str | None
    is_active: bool
    assigned_at: datetime


class PolicyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    is_default: bool = False
    attendance_window_seconds: int = Field(default=180, ge=30, le=7200)
    qr_refresh_seconds: int = Field(default=30, ge=5, le=600)
    qr_grace_seconds: int = Field(default=15, ge=0, le=300)
    require_pin: bool = True
    require_geofence: bool = True
    require_face: bool = False
    require_liveness: bool = False
    allow_review_outside_geofence: bool = True
    presence_monitoring_enabled: bool = False
    full_presence_ratio: float = Field(default=0.8, ge=0, le=1)
    partial_presence_ratio: float = Field(default=0.5, ge=0, le=1)


class PolicyUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    is_default: bool | None = None
    attendance_window_seconds: int | None = Field(default=None, ge=30, le=7200)
    qr_refresh_seconds: int | None = Field(default=None, ge=5, le=600)
    qr_grace_seconds: int | None = Field(default=None, ge=0, le=300)
    require_pin: bool | None = None
    require_geofence: bool | None = None
    require_face: bool | None = None
    require_liveness: bool | None = None
    allow_review_outside_geofence: bool | None = None
    presence_monitoring_enabled: bool | None = None
    full_presence_ratio: float | None = Field(default=None, ge=0, le=1)
    partial_presence_ratio: float | None = Field(default=None, ge=0, le=1)


class PolicyOut(ORMModel):
    id: uuid.UUID
    name: str
    is_default: bool
    attendance_window_seconds: int
    qr_refresh_seconds: int
    qr_grace_seconds: int
    require_pin: bool
    require_geofence: bool
    require_face: bool
    require_liveness: bool
    allow_review_outside_geofence: bool
    presence_monitoring_enabled: bool
    full_presence_ratio: float
    partial_presence_ratio: float


class GeofenceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    classroom_id: uuid.UUID | None = None
    center_latitude: float = Field(ge=-90, le=90)
    center_longitude: float = Field(ge=-180, le=180)
    radius_m: float = Field(default=60.0, ge=5, le=2000)
    max_accuracy_m: float = Field(default=100.0, ge=5, le=2000)
    allow_review_outside: bool = True


class GeofenceOut(ORMModel):
    id: uuid.UUID
    name: str
    classroom_id: uuid.UUID | None
    center_latitude: float
    center_longitude: float
    radius_m: float
    max_accuracy_m: float
    allow_review_outside: bool
    is_active: bool
