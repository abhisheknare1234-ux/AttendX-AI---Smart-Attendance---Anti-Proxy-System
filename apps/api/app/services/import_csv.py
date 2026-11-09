"""CSV provisioning: template, validated preview and transactional commit.

No sample records are generated here. Every row comes from an administrator's
file and every created account is audited.
"""
from __future__ import annotations

import csv
import io
import uuid

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import errors
from app.core.timeutil import utcnow
from app.models import ImportJob, ImportStatus, StudentProfile, TeacherProfile, User, UserRole
from app.schemas.accounts import ImportCommitResponse, ImportPreviewResponse, ImportRowResult
from app.services.users import provision_student, provision_teacher

STUDENT_HEADERS = [
    "email",
    "full_name",
    "roll_number",
    "department",
    "programme",
    "year",
    "division",
    "batch",
    "admission_year",
    "phone",
]
TEACHER_HEADERS = [
    "email",
    "full_name",
    "employee_id",
    "department",
    "designation",
    "phone",
]


def template_csv(kind: str) -> str:
    headers = STUDENT_HEADERS if kind == "students" else TEACHER_HEADERS
    example = (
        "student@example.edu,Full Name,ROLL-001,Computer Engineering,B.E.,2,A,2024,2024,"
        if kind == "students"
        else "teacher@example.edu,Full Name,EMP-001,Computer Engineering,Assistant Professor,"
    )
    return ",".join(headers) + "\n" + example + "\n"


def _read_rows(content: bytes) -> list[dict[str, str]]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise errors.bad_request("The CSV must be UTF-8 encoded.", "INVALID_ENCODING")
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise errors.bad_request("The CSV file has no header row.", "INVALID_CSV")
    return [{(k or "").strip().lower(): (v or "").strip() for k, v in row.items()} for row in reader]


def _validate_email(value: str) -> str | None:
    if not value:
        return "Email is required."
    try:
        validate_email(value, check_deliverability=False)
    except EmailNotValidError as exc:
        return f"Invalid email: {exc}"
    return None


def _existing_email(db: Session, email: str) -> bool:
    return (
        db.scalar(select(User.id).where(func.lower(User.email) == email.lower())) is not None
    )


def preview(db: Session, *, kind: str, content: bytes) -> ImportPreviewResponse:
    headers = STUDENT_HEADERS if kind == "students" else TEACHER_HEADERS
    if kind not in {"students", "teachers"}:
        raise errors.bad_request("Import kind must be students or teachers.", "INVALID_KIND")
    rows = _read_rows(content)
    if not rows:
        raise errors.bad_request("The CSV file contains no data rows.", "EMPTY_CSV")

    seen_emails: set[str] = set()
    seen_identifiers: set[str] = set()
    results: list[ImportRowResult] = []
    duplicates = 0

    for index, row in enumerate(rows, start=2):
        row_errors: list[str] = []
        email = row.get("email", "").lower()
        email_error = _validate_email(email)
        if email_error:
            row_errors.append(email_error)
        if email and email in seen_emails:
            row_errors.append("Duplicate email within this file.")
            duplicates += 1
        seen_emails.add(email)

        full_name = row.get("full_name", "")
        if len(full_name) < 2:
            row_errors.append("Full name is required.")

        department = row.get("department", "")
        if not department:
            row_errors.append("Department is required.")

        if kind == "students":
            roll = row.get("roll_number", "")
            if not roll:
                row_errors.append("Roll number is required.")
            elif roll in seen_identifiers:
                row_errors.append("Duplicate roll number within this file.")
            seen_identifiers.add(roll)
            year_raw = row.get("year", "1")
            try:
                year = int(year_raw)
                if not 1 <= year <= 6:
                    raise ValueError
            except ValueError:
                row_errors.append("Year must be a whole number from 1 to 6.")
            admission_raw = row.get("admission_year", "")
            if admission_raw:
                try:
                    int(admission_raw)
                except ValueError:
                    row_errors.append("Admission year must be numeric.")
            if roll and db.scalar(
                select(StudentProfile.id).where(StudentProfile.roll_number == roll)
            ):
                row_errors.append("A student with this roll number already exists.")
        else:
            employee_id = row.get("employee_id", "")
            if not employee_id:
                row_errors.append("Employee ID is required.")
            elif employee_id in seen_identifiers:
                row_errors.append("Duplicate employee ID within this file.")
            seen_identifiers.add(employee_id)
            if employee_id and db.scalar(
                select(TeacherProfile.id).where(TeacherProfile.employee_id == employee_id)
            ):
                row_errors.append("A teacher with this employee ID already exists.")

        if email and _existing_email(db, email):
            row_errors.append("An account with this email already exists.")

        results.append(
            ImportRowResult(
                row_number=index,
                ok=not row_errors,
                errors=row_errors,
                data={key: row.get(key, "") for key in headers},
            )
        )

    valid = sum(1 for row in results if row.ok)
    return ImportPreviewResponse(
        kind=kind,
        total_rows=len(results),
        valid_rows=valid,
        invalid_rows=len(results) - valid,
        duplicate_rows=duplicates,
        rows=results,
    )


def commit(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    kind: str,
    content: bytes,
    filename: str | None,
) -> ImportCommitResponse:
    preview_result = preview(db, kind=kind, content=content)
    job = ImportJob(
        actor_user_id=actor_user_id,
        kind=kind,
        filename=filename,
        status=ImportStatus.PREVIEWED,
        total_rows=preview_result.total_rows,
    )
    db.add(job)
    db.flush()

    created: list[dict] = []
    errors: list[dict] = []
    try:
        for row in preview_result.rows:
            if not row.ok:
                errors.append({"row_number": row.row_number, "errors": row.errors})
                continue
            data = row.data
            try:
                if kind == "students":
                    user, temp = provision_student(
                        db,
                        actor_user_id=actor_user_id,
                        email=data["email"],
                        full_name=data["full_name"],
                        password=None,
                        roll_number=data["roll_number"],
                        department=data["department"],
                        programme=data.get("programme") or "B.E.",
                        year=int(data.get("year") or 1),
                        division=data.get("division") or "A",
                        batch=data.get("batch") or None,
                        admission_year=int(data["admission_year"]) if data.get("admission_year") else None,
                        phone=data.get("phone") or None,
                    )
                else:
                    user, temp = provision_teacher(
                        db,
                        actor_user_id=actor_user_id,
                        email=data["email"],
                        full_name=data["full_name"],
                        password=None,
                        employee_id=data["employee_id"],
                        department=data["department"],
                        designation=data.get("designation") or None,
                        phone=data.get("phone") or None,
                    )
            except errors.ApiError as exc:
                errors.append(
                    {"row_number": row.row_number, "errors": [exc.detail.get("message", "Invalid row")]}  # type: ignore[union-attr]
                )
                continue
            created.append(
                {
                    "id": str(user.id),
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.value,
                    "temporary_password": temp,
                }
            )
        job.success_rows = len(created)
        job.error_rows = len(errors)
        job.errors = errors
        job.status = ImportStatus.COMMITTED
        job.completed_at = utcnow()
        db.commit()
    except IntegrityError:
        db.rollback()
        failed_job = ImportJob(
            actor_user_id=actor_user_id,
            kind=kind,
            filename=filename,
            status=ImportStatus.FAILED,
            total_rows=preview_result.total_rows,
            success_rows=0,
            error_rows=preview_result.total_rows,
            errors=[{"error": "The import conflicted with existing records; no rows were created."}],
            completed_at=utcnow(),
        )
        db.add(failed_job)
        db.commit()
        raise errors.conflict(
            "The import conflicted with existing records. No accounts were created.",
            "IMPORT_CONFLICT",
        )

    return ImportCommitResponse(
        job_id=job.id,
        status=job.status,
        total_rows=job.total_rows,
        success_rows=job.success_rows,
        error_rows=job.error_rows,
        errors=job.errors or [],
        created_users=created,
    )
