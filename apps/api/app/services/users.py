"""Account provisioning and user serialization."""
from __future__ import annotations

import secrets
import string

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.security import hash_password, password_problem
from app.models import (
    StudentProfile,
    TeacherProfile,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.accounts import StudentSummary, TeacherSummary, UserOut
from app.services import audit as audit_service


def temporary_password() -> str:
    """Generate a one-time password that satisfies the provisioning policy."""
    alphabet = string.ascii_letters + string.digits
    body = "".join(secrets.choice(alphabet) for _ in range(12))
    return f"Ax{body}9"


def user_out(db: Session, user: User) -> UserOut:
    student = None
    teacher = None
    if user.role == UserRole.STUDENT:
        profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user.id))
        if profile:
            student = StudentSummary.model_validate(profile)
    elif user.role == UserRole.TEACHER:
        profile = db.scalar(select(TeacherProfile).where(TeacherProfile.user_id == user.id))
        if profile:
            teacher = TeacherSummary.model_validate(profile)
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        status=user.status,
        must_change_password=user.must_change_password,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        student=student,
        teacher=teacher,
    )


def _ensure_unique_email(db: Session, email: str, *, exclude_user_id=None) -> None:
    query = select(User.id).where(func.lower(User.email) == email.strip().lower())
    if exclude_user_id is not None:
        query = query.where(User.id != exclude_user_id)
    if db.scalar(query) is not None:
        raise errors.conflict("An account with this email already exists.", "EMAIL_EXISTS")


def _resolve_password(password: str | None) -> tuple[str, bool]:
    """Returns (password, was_generated)."""
    if password is None:
        return temporary_password(), True
    problem = password_problem(password)
    if problem:
        raise errors.bad_request(problem, "WEAK_PASSWORD")
    return password, False


def provision_admin(
    db: Session,
    *,
    email: str,
    full_name: str,
    password: str | None,
    actor_user_id=None,
) -> tuple[User, str | None]:
    email = email.strip().lower()
    _ensure_unique_email(db, email)
    plain, generated = _resolve_password(password)
    user = User(
        email=email,
        full_name=full_name.strip(),
        password_hash=hash_password(plain),
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
        must_change_password=generated,
    )
    db.add(user)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="USER_PROVISIONED",
        entity_type="user",
        entity_id=user.id,
        details={"role": "admin", "temporary_password": generated},
    )
    return user, plain if generated else None


def provision_student(
    db: Session,
    *,
    actor_user_id,
    email: str,
    full_name: str,
    password: str | None,
    roll_number: str,
    department: str,
    programme: str,
    year: int,
    division: str,
    batch: str | None,
    admission_year: int | None,
    phone: str | None = None,
) -> tuple[User, str | None]:
    email = email.strip().lower()
    _ensure_unique_email(db, email)
    if db.scalar(select(StudentProfile.id).where(StudentProfile.roll_number == roll_number.strip())):
        raise errors.conflict("A student with this roll number already exists.", "ROLL_EXISTS")
    plain, generated = _resolve_password(password)
    user = User(
        email=email,
        full_name=full_name.strip(),
        phone=phone,
        password_hash=hash_password(plain),
        role=UserRole.STUDENT,
        status=UserStatus.ACTIVE,
        must_change_password=generated,
    )
    db.add(user)
    db.flush()
    profile = StudentProfile(
        user_id=user.id,
        roll_number=roll_number.strip(),
        department=department.strip(),
        programme=programme.strip(),
        year=year,
        division=division.strip(),
        batch=batch,
        admission_year=admission_year,
    )
    db.add(profile)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="STUDENT_PROVISIONED",
        entity_type="student_profile",
        entity_id=profile.id,
        details={"user_id": str(user.id), "roll_number": profile.roll_number},
    )
    return user, plain if generated else None


def provision_teacher(
    db: Session,
    *,
    actor_user_id,
    email: str,
    full_name: str,
    password: str | None,
    employee_id: str,
    department: str,
    designation: str | None,
    phone: str | None = None,
) -> tuple[User, str | None]:
    email = email.strip().lower()
    _ensure_unique_email(db, email)
    if db.scalar(select(TeacherProfile.id).where(TeacherProfile.employee_id == employee_id.strip())):
        raise errors.conflict("A teacher with this employee ID already exists.", "EMPLOYEE_EXISTS")
    plain, generated = _resolve_password(password)
    user = User(
        email=email,
        full_name=full_name.strip(),
        phone=phone,
        password_hash=hash_password(plain),
        role=UserRole.TEACHER,
        status=UserStatus.ACTIVE,
        must_change_password=generated,
    )
    db.add(user)
    db.flush()
    profile = TeacherProfile(
        user_id=user.id,
        employee_id=employee_id.strip(),
        department=department.strip(),
        designation=designation.strip() if designation else None,
    )
    db.add(profile)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="TEACHER_PROVISIONED",
        entity_type="teacher_profile",
        entity_id=profile.id,
        details={"user_id": str(user.id), "employee_id": profile.employee_id},
    )
    return user, plain if generated else None
