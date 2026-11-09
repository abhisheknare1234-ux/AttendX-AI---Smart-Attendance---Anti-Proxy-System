"""Pydantic request/response schemas for identity, auth and administration."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ImportStatus, UserRole, UserStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class StudentSummary(ORMModel):
    id: uuid.UUID
    roll_number: str
    department: str
    programme: str
    year: int
    division: str
    batch: str | None = None


class TeacherSummary(ORMModel):
    id: uuid.UUID
    employee_id: str
    department: str
    designation: str | None = None


class UserOut(ORMModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    must_change_password: bool
    last_login_at: datetime | None = None
    created_at: datetime
    student: StudentSummary | None = None
    teacher: TeacherSummary | None = None


class MeResponse(BaseModel):
    user: UserOut
    csrf_token: str


class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    role: UserRole = UserRole.TEACHER
    password: str | None = Field(default=None, max_length=128)


class StudentCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str | None = Field(default=None, max_length=128)
    roll_number: str = Field(min_length=1, max_length=40)
    department: str = Field(min_length=1, max_length=120)
    programme: str = Field(default="B.E.", max_length=120)
    year: int = Field(default=1, ge=1, le=6)
    division: str = Field(default="A", max_length=10)
    batch: str | None = Field(default=None, max_length=20)
    admission_year: int | None = Field(default=None, ge=1950, le=2100)
    phone: str | None = Field(default=None, max_length=32)


class TeacherCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=160)
    password: str | None = Field(default=None, max_length=128)
    employee_id: str = Field(min_length=1, max_length=40)
    department: str = Field(min_length=1, max_length=120)
    designation: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=32)


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    status: UserStatus | None = None
    must_change_password: bool | None = None
    new_password: str | None = Field(default=None, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=10, max_length=128)


class ProvisionedUserResponse(BaseModel):
    user: UserOut
    temporary_password: str | None = None


class ImportRowResult(BaseModel):
    row_number: int
    ok: bool
    errors: list[str] = Field(default_factory=list)
    data: dict = Field(default_factory=dict)


class ImportPreviewResponse(BaseModel):
    kind: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    rows: list[ImportRowResult]


class ImportCommitResponse(BaseModel):
    job_id: uuid.UUID
    status: ImportStatus
    total_rows: int
    success_rows: int
    error_rows: int
    errors: list[dict] = Field(default_factory=list)
    created_users: list[dict] = Field(default_factory=list)


class AuditEventOut(ORMModel):
    id: uuid.UUID
    actor_user_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: str | None
    details: dict | None
    ip_address: str | None
    created_at: datetime


class SecurityEventOut(ORMModel):
    id: uuid.UUID
    event_type: str
    severity: str
    user_id: uuid.UUID | None
    session_id: uuid.UUID | None
    ip_address: str | None
    details: dict | None
    created_at: datetime


class HealthOut(BaseModel):
    status: str
    database: str
    face_provider: str
    liveness_provider: str
    environment: str
    version: str
