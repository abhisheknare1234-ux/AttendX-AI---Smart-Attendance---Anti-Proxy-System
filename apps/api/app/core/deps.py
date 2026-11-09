"""Authentication and authorization dependencies."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.security import constant_time_equals, token_hash
from app.core.timeutil import utcnow
from app.models import AuthSession, StudentProfile, TeacherProfile, User, UserRole, UserStatus


@dataclass(slots=True)
class AuthContext:
    user: User
    session: AuthSession
    student_id: uuid.UUID | None
    teacher_id: uuid.UUID | None

    @property
    def role(self) -> UserRole:
        return self.user.role


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _resolve_profile(db: Session, user: User) -> tuple[uuid.UUID | None, uuid.UUID | None]:
    if user.role == UserRole.STUDENT:
        student = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        return (student.id if student else None), None
    if user.role == UserRole.TEACHER:
        teacher = db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == user.id))
        return None, (teacher.id if teacher else None)
    return None, None


def get_current_auth(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthContext:
    raw_token = request.cookies.get(settings.session_cookie_name)
    if not raw_token:
        raise errors.unauthorized()

    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash(raw_token)))
    now = utcnow()
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
    ):
        raise errors.unauthorized("Your session has expired. Please sign in again.")

    user = db.get(User, session.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise errors.unauthorized("This account is not active.")

    if session.last_seen_at is None or (now - session.last_seen_at) > timedelta(seconds=60):
        session.last_seen_at = now
        db.commit()

    student_id, teacher_id = _resolve_profile(db, user)
    return AuthContext(user=user, session=session, student_id=student_id, teacher_id=teacher_id)


def require_csrf(
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
) -> AuthContext:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return auth
    provided = request.headers.get("X-CSRF-Token", "")
    if not provided or not constant_time_equals(provided, auth.session.csrf_token):
        raise errors.ApiError(
            403,
            "CSRF_FAILED",
            "The security token for this request is missing or invalid. Refresh the page and try again.",
        )
    return auth


def require_role(*roles: UserRole):
    def dependency(auth: AuthContext = Depends(get_current_auth)) -> AuthContext:
        if auth.user.role not in roles:
            raise errors.forbidden()
        return auth

    return dependency


require_admin = require_role(UserRole.ADMIN)
require_teacher = require_role(UserRole.TEACHER)
require_student = require_role(UserRole.STUDENT)
require_staff = require_role(UserRole.ADMIN, UserRole.TEACHER)


def require_student_profile(auth: AuthContext = Depends(require_student)) -> AuthContext:
    if auth.student_id is None:
        raise errors.forbidden("No student profile is linked to this account.")
    return auth


def require_teacher_profile(auth: AuthContext = Depends(require_teacher)) -> AuthContext:
    if auth.teacher_id is None:
        raise errors.forbidden("No teacher profile is linked to this account.")
    return auth
