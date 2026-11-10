"""Attendance domain service: sessions, rotating QR, PIN, location, face/liveness
evidence, risk decision and final records."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings
from app.core.rate_limit import check_rate_limit
from app.core.security import (
    generate_pin,
    generate_reference,
    generate_token,
    hash_pin,
    sign_qr_payload,
    verify_pin,
    verify_qr_signature,
)
from app.core.timeutil import parse_client_timestamp, utcnow
from app.models import (
    AttendanceAttempt,
    AttendanceClassification,
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    AttemptStatus,
    ClassEnrollment,
    Classroom,
    DecisionSource,
    EnrollmentStatus,
    FactorStatus,
    GeofencePolicy,
    GpsStatus,
    QrToken,
    RiskDecision,
    SchoolClass,
    SecuritySeverity,
    SessionStatus,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
    User,
    VerificationEvidence,
)
from app.providers.verification import (
    VerificationResult,
    get_face_provider,
    get_liveness_provider,
)
from app.schemas.attendance import (
    AttemptOut,
    FinalizeResponse,
    LiveAttemptOut,
    LiveSessionResponse,
    OpenSessionResponse,
    QrOut,
    QrValidateResponse,
    RequirementsOut,
    SessionOut,
)
from app.services import audit as audit_service
from app.services.geofence import GeofenceConfig, evaluate_location
from app.services.risk import RequiredFactors, RiskInput, evaluate_risk


# ---------------------------------------------------------------------------
# Lookups and builders
# ---------------------------------------------------------------------------
def get_session(db: Session, session_id: uuid.UUID) -> AttendanceSession:
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise errors.not_found("Attendance session not found.")
    return session


def teacher_owns_session(db: Session, session: AttendanceSession, teacher_id: uuid.UUID) -> bool:
    return session.teacher_id == teacher_id


def teacher_assignment(
    db: Session, teacher_id: uuid.UUID, class_id: uuid.UUID, subject_id: uuid.UUID
) -> TeacherAssignment | None:
    return db.scalar(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher_id,
            TeacherAssignment.class_id == class_id,
            TeacherAssignment.is_active.is_(True),
            (TeacherAssignment.subject_id == subject_id) | (TeacherAssignment.subject_id.is_(None)),
        )
    )


def _context(db: Session, session: AttendanceSession) -> dict:
    school_class = db.get(SchoolClass, session.class_id)
    subject = db.get(Subject, session.subject_id)
    classroom = db.get(Classroom, session.classroom_id)
    teacher = db.get(TeacherProfile, session.teacher_id)
    teacher_user = db.get(User, teacher.user_id) if teacher else None
    return {
        "class": school_class,
        "subject": subject,
        "classroom": classroom,
        "teacher": teacher,
        "teacher_user": teacher_user,
    }


def session_counts(db: Session, session_id: uuid.UUID) -> dict[str, int]:
    session_obj = db.get(AttendanceSession, session_id)
    eligible = 0
    if session_obj is not None:
        eligible = len(
            db.scalars(
                select(ClassEnrollment.id).where(
                    ClassEnrollment.class_id == session_obj.class_id,
                    ClassEnrollment.status == EnrollmentStatus.ACTIVE,
                )
            ).all()
        )
    rows = db.execute(
        select(AttendanceAttempt.status, AttendanceAttempt.student_id).where(
            AttendanceAttempt.session_id == session_id
        )
    ).all()
    seen: dict[str, set[uuid.UUID]] = {}
    for status, student_id in rows:
        seen.setdefault(status.value if hasattr(status, "value") else str(status), set()).add(student_id)
    return {
        "eligible_students": eligible,
        "accepted": len(seen.get(AttemptStatus.ACCEPTED.value, set())),
        "pending": len(seen.get(AttemptStatus.IN_PROGRESS.value, set())),
        "rejected": len(seen.get(AttemptStatus.REJECTED.value, set())),
        "review_required": len(seen.get(AttemptStatus.REVIEW_REQUIRED.value, set())),
    }


def session_out(db: Session, session: AttendanceSession) -> SessionOut:
    context = _context(db, session)
    counts = session_counts(db, session.id)
    school_class = context["class"]
    subject = context["subject"]
    classroom = context["classroom"]
    teacher_user = context["teacher_user"]
    return SessionOut(
        id=session.id,
        class_id=session.class_id,
        class_code=school_class.code if school_class else "",
        class_name=school_class.name if school_class else "",
        subject_id=session.subject_id,
        subject_code=subject.code if subject else "",
        subject_name=subject.name if subject else "",
        classroom_id=session.classroom_id,
        classroom_name=classroom.name if classroom else "",
        teacher_id=session.teacher_id,
        teacher_name=teacher_user.full_name if teacher_user else "",
        status=session.status,
        starts_at=session.starts_at,
        ends_at=session.ends_at,
        window_seconds=session.window_seconds,
        qr_refresh_seconds=session.qr_refresh_seconds,
        qr_grace_seconds=session.qr_grace_seconds,
        require_pin=session.require_pin,
        require_geofence=session.require_geofence,
        require_face=session.require_face,
        require_liveness=session.require_liveness,
        allow_review_outside_geofence=session.allow_review_outside_geofence,
        pin_available=bool(session.pin_hash),
        opened_at=session.opened_at,
        closed_at=session.closed_at,
        created_at=session.created_at,
        **counts,
    )


def qr_out(row: QrToken, settings: Settings, refresh_seconds: int | None = None) -> QrOut:
    payload = {
        "sid": str(row.session_id),
        "nonce": row.nonce,
        "iat": int(row.issued_at.timestamp()),
        "exp": int(row.expires_at.timestamp()),
    }
    token = sign_qr_payload(payload, settings.qr_signing_key)
    base = settings.web_origin.rstrip("/")
    return QrOut(
        token=token,
        url=f"{base}/attend/{token}",
        issued_at=row.issued_at,
        expires_at=row.expires_at,
        refresh_seconds=refresh_seconds or settings.default_qr_refresh_seconds,
        session_id=row.session_id,
    )


def _create_qr_row(
    db: Session, session: AttendanceSession, actor_user_id: uuid.UUID, settings: Settings
) -> QrToken:
    now = utcnow()
    refresh = session.qr_refresh_seconds or settings.default_qr_refresh_seconds
    grace = session.qr_grace_seconds if session.qr_grace_seconds is not None else settings.qr_grace_seconds
    expires_at = now + timedelta(seconds=refresh + grace)
    if session.ends_at and expires_at > session.ends_at + timedelta(seconds=grace):
        expires_at = session.ends_at + timedelta(seconds=grace)
    if expires_at <= now:
        raise errors.bad_request("The attendance window has already closed.", "WINDOW_CLOSED")
    row = QrToken(
        session_id=session.id,
        nonce=generate_token(18),
        issued_at=now,
        expires_at=expires_at,
        created_by_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    return row


def current_qr(
    db: Session, session: AttendanceSession, actor_user_id: uuid.UUID, settings: Settings
) -> QrToken:
    now = utcnow()
    row = db.scalar(
        select(QrToken)
        .where(
            QrToken.session_id == session.id,
            QrToken.revoked_at.is_(None),
            QrToken.expires_at > now + timedelta(seconds=2),
        )
        .order_by(QrToken.expires_at.desc())
    )
    if row is None:
        row = _create_qr_row(db, session, actor_user_id, settings)
        db.commit()
        db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Session lifecycle
# ---------------------------------------------------------------------------
def create_session(
    db: Session,
    *,
    actor_user_id: uuid.UUID,
    teacher_id: uuid.UUID,
    payload,  # SessionCreateRequest
    settings: Settings,
) -> AttendanceSession:
    school_class = db.get(SchoolClass, payload.class_id)
    subject = db.get(Subject, payload.subject_id)
    classroom = db.get(Classroom, payload.classroom_id)
    if school_class is None:
        raise errors.not_found("Class not found.")
    if subject is None or subject.class_id != school_class.id:
        raise errors.bad_request("The subject does not belong to the selected class.", "SUBJECT_CLASS_MISMATCH")
    if classroom is None:
        raise errors.not_found("Classroom not found.")
    if teacher_assignment(db, teacher_id, school_class.id, subject.id) is None:
        raise errors.forbidden("You are not assigned to this class and subject.")

    policy: AttendancePolicy | None = None
    if payload.policy_id is not None:
        policy = db.get(AttendancePolicy, payload.policy_id)
        if policy is None:
            raise errors.not_found("Attendance policy not found.")
    else:
        policy = db.scalar(select(AttendancePolicy).where(AttendancePolicy.is_default.is_(True)))
    if payload.geofence_id is not None and db.get(GeofencePolicy, payload.geofence_id) is None:
        raise errors.not_found("Geofence policy not found.")

    starts_at = payload.starts_at
    if starts_at.tzinfo is None:
        raise errors.bad_request("starts_at must include a timezone offset.", "INVALID_TIME")
    window_seconds = payload.window_seconds or (
        policy.attendance_window_seconds if policy else settings.default_attendance_window_seconds
    )
    if payload.ends_at is not None:
        ends_at = payload.ends_at
        if ends_at.tzinfo is None:
            raise errors.bad_request("ends_at must include a timezone offset.", "INVALID_TIME")
        window_seconds = int((ends_at - starts_at).total_seconds())
    else:
        ends_at = starts_at + timedelta(seconds=window_seconds)

    qr_refresh = payload.qr_refresh_seconds or (
        policy.qr_refresh_seconds if policy else settings.default_qr_refresh_seconds
    )
    require_pin = payload.require_pin if payload.require_pin is not None else (policy.require_pin if policy else True)
    require_geofence = (
        payload.require_geofence
        if payload.require_geofence is not None
        else (policy.require_geofence if policy else True)
    )
    require_face = (
        payload.require_face if payload.require_face is not None else (policy.require_face if policy else False)
    )
    require_liveness = (
        payload.require_liveness
        if payload.require_liveness is not None
        else (policy.require_liveness if policy else False)
    )
    allow_review = policy.allow_review_outside_geofence if policy else True

    session = AttendanceSession(
        class_id=school_class.id,
        subject_id=subject.id,
        classroom_id=classroom.id,
        teacher_id=teacher_id,
        policy_id=policy.id if policy else None,
        geofence_id=payload.geofence_id,
        status=SessionStatus.SCHEDULED,
        starts_at=starts_at,
        ends_at=ends_at,
        window_seconds=window_seconds,
        qr_refresh_seconds=qr_refresh,
        qr_grace_seconds=policy.qr_grace_seconds if policy else settings.qr_grace_seconds,
        require_pin=require_pin,
        require_geofence=require_geofence,
        require_face=require_face,
        require_liveness=require_liveness,
        allow_review_outside_geofence=allow_review,
        created_by_id=actor_user_id,
    )
    db.add(session)
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="SESSION_CREATED",
        entity_type="attendance_session",
        entity_id=session.id,
        details={
            "class_id": str(school_class.id),
            "subject_id": str(subject.id),
            "starts_at": starts_at.isoformat(),
            "window_seconds": window_seconds,
        },
    )
    db.commit()
    db.refresh(session)
    return session


def open_session(
    db: Session,
    *,
    session: AttendanceSession,
    actor_user_id: uuid.UUID,
    settings: Settings,
) -> tuple[AttendanceSession, str | None, QrToken]:
    if session.status == SessionStatus.OPEN:
        row = current_qr(db, session, actor_user_id, settings)
        return session, None, row
    if session.status not in {SessionStatus.SCHEDULED}:
        raise errors.conflict("This session cannot be opened from its current state.", "SESSION_STATE")
    now = utcnow()
    if now < session.starts_at - timedelta(minutes=10):
        raise errors.bad_request(
            "This session cannot be opened more than 10 minutes before its scheduled start.",
            "SESSION_NOT_DUE",
        )
    if now >= session.ends_at:
        raise errors.bad_request("The planned attendance window has already elapsed.", "WINDOW_ELAPSED")

    session.status = SessionStatus.OPEN
    session.opened_at = now
    # The check-in window runs from the moment the session is opened, so a late
    # start still gives students the configured window.
    session.ends_at = now + timedelta(seconds=session.window_seconds)
    pin: str | None = None
    if session.require_pin:
        pin = generate_pin(settings.pin_length)
        session.pin_hash = hash_pin(pin)
        session.pin_expires_at = session.ends_at + timedelta(seconds=settings.pin_expiry_grace_seconds)
    row = _create_qr_row(db, session, actor_user_id, settings)
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="SESSION_OPENED",
        entity_type="attendance_session",
        entity_id=session.id,
        details={"ends_at": session.ends_at.isoformat(), "pin_enabled": session.require_pin},
    )
    db.commit()
    db.refresh(session)
    db.refresh(row)
    return session, pin, row


def close_session(
    db: Session, *, session: AttendanceSession, actor_user_id: uuid.UUID
) -> AttendanceSession:
    if session.status != SessionStatus.OPEN:
        raise errors.conflict("Only an open session can be closed.", "SESSION_STATE")
    now = utcnow()
    session.status = SessionStatus.CLOSED
    session.closed_at = now
    session.closed_by_id = actor_user_id
    session.pin_hash = None
    session.pin_expires_at = None
    db.execute(
        update(QrToken)
        .where(QrToken.session_id == session.id, QrToken.revoked_at.is_(None))
        .values(revoked_at=now)
    )
    abandoned = db.scalars(
        select(AttendanceAttempt).where(
            AttendanceAttempt.session_id == session.id,
            AttendanceAttempt.status == AttemptStatus.IN_PROGRESS,
        )
    ).all()
    for attempt in abandoned:
        attempt.status = AttemptStatus.ABANDONED
        attempt.completed_at = now
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="SESSION_CLOSED",
        entity_type="attendance_session",
        entity_id=session.id,
        details={"abandoned_attempts": len(abandoned)},
    )
    db.commit()
    db.refresh(session)
    return session


def rotate_qr(
    db: Session,
    *,
    session: AttendanceSession,
    actor_user_id: uuid.UUID,
    settings: Settings,
) -> QrToken:
    if session.status != SessionStatus.OPEN:
        raise errors.conflict("The session is not open.", "SESSION_NOT_OPEN")
    if utcnow() >= session.ends_at:
        raise errors.bad_request("The attendance window has closed.", "WINDOW_CLOSED")
    row = _create_qr_row(db, session, actor_user_id, settings)
    db.commit()
    db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# QR validation and attempt lifecycle
# ---------------------------------------------------------------------------
def validate_qr(
    db: Session, token: str, settings: Settings
) -> tuple[QrToken, AttendanceSession]:
    payload = verify_qr_signature(token, settings.qr_signing_key)
    if payload is None:
        raise errors.bad_request("This attendance QR code is not valid.", "QR_INVALID")
    try:
        session_id = uuid.UUID(str(payload["sid"]))
        nonce = str(payload["nonce"])
        exp = int(payload["exp"])
    except (ValueError, KeyError, TypeError):
        raise errors.bad_request("This attendance QR code is not valid.", "QR_INVALID")

    row = db.scalar(
        select(QrToken).where(QrToken.session_id == session_id, QrToken.nonce == nonce)
    )
    now = utcnow()
    if row is None or row.revoked_at is not None:
        raise errors.bad_request("This attendance QR code is no longer active.", "QR_REVOKED")
    if row.expires_at <= now or exp <= int(now.timestamp()):
        raise errors.bad_request(
            "This QR code has expired. Scan the teacher's current QR code.", "QR_EXPIRED"
        )

    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise errors.not_found("Attendance session not found.")
    if session.status != SessionStatus.OPEN:
        raise errors.conflict("This attendance session is not open.", "SESSION_NOT_OPEN")
    if now >= session.ends_at:
        session.status = SessionStatus.EXPIRED
        db.commit()
        raise errors.conflict("The attendance window for this session has closed.", "SESSION_EXPIRED")
    return row, session


def ensure_enrolled(db: Session, session: AttendanceSession, student_id: uuid.UUID) -> None:
    enrollment = db.scalar(
        select(ClassEnrollment).where(
            ClassEnrollment.class_id == session.class_id,
            ClassEnrollment.student_id == student_id,
            ClassEnrollment.status == EnrollmentStatus.ACTIVE,
        )
    )
    if enrollment is None:
        raise errors.forbidden("You are not enrolled in this class.")

    student = db.get(StudentProfile, student_id)
    if student is None or student.user_id is None:
        raise errors.forbidden("Student profile not found.")


def existing_record(
    db: Session, session_id: uuid.UUID, student_id: uuid.UUID
) -> AttendanceRecord | None:
    return db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    )


def requirements(session: AttendanceSession) -> RequirementsOut:
    return RequirementsOut(
        pin=session.require_pin,
        geofence=session.require_geofence,
        face=session.require_face,
        liveness=session.require_liveness,
    )


def required_steps(session: AttendanceSession) -> list[str]:
    steps: list[str] = []
    if session.require_pin:
        steps.append("pin")
    if session.require_geofence:
        steps.append("gps")
    if session.require_face:
        steps.append("face")
    if session.require_liveness:
        steps.append("liveness")
    return steps


def next_step(attempt: AttendanceAttempt, session: AttendanceSession) -> str | None:
    if session.require_pin and attempt.pin_status != FactorStatus.PASSED:
        return "pin"
    if session.require_geofence and attempt.gps_submitted_at is None:
        return "gps"
    if session.require_face and attempt.face_status in {
        FactorStatus.PENDING,
        FactorStatus.NOT_SUBMITTED,
    }:
        return "face"
    if session.require_liveness and attempt.liveness_status in {
        FactorStatus.PENDING,
        FactorStatus.NOT_SUBMITTED,
    }:
        return "liveness"
    return None


def qr_validate_response(
    db: Session, session: AttendanceSession, student_id: uuid.UUID, settings: Settings
) -> QrValidateResponse:
    context = _context(db, session)
    now = utcnow()
    record = existing_record(db, session.id, student_id)
    remaining = max(0, int((session.ends_at - now).total_seconds()))
    open_session_now = session.status == SessionStatus.OPEN and remaining > 0
    if record is not None:
        can_check_in = False
        message = "Attendance has already been recorded for this session."
        existing = record.status
    elif open_session_now:
        can_check_in = True
        message = "Session is open. Continue with the required verification steps."
        existing = None
    elif session.status == SessionStatus.SCHEDULED:
        can_check_in = False
        message = "This session has not been opened by the teacher yet."
        existing = None
    else:
        can_check_in = False
        message = "This attendance session is closed."
        existing = None
    return QrValidateResponse(
        session_id=session.id,
        class_name=context["class"].name if context["class"] else "",
        subject_name=context["subject"].name if context["subject"] else "",
        classroom_name=context["classroom"].name if context["classroom"] else "",
        teacher_name=context["teacher_user"].full_name if context["teacher_user"] else "",
        status=session.status,
        starts_at=session.starts_at,
        ends_at=session.ends_at,
        seconds_remaining=remaining,
        requirements=requirements(session),
        already_recorded=record is not None,
        existing_status=existing,
        can_check_in=can_check_in,
        message=message,
    )


def attempt_out(attempt: AttendanceAttempt) -> AttemptOut:
    return AttemptOut(
        id=attempt.id,
        reference=attempt.reference,
        session_id=attempt.session_id,
        status=attempt.status,
        current_step=attempt.current_step,
        qr_status=attempt.qr_status,
        pin_status=attempt.pin_status,
        gps_status=attempt.gps_status,
        face_status=attempt.face_status,
        liveness_status=attempt.liveness_status,
        pin_attempts=attempt.pin_attempts,
        gps_distance_m=attempt.gps_distance_m,
        gps_accuracy_m=attempt.gps_accuracy_m,
        risk_score=attempt.risk_score,
        risk_decision=attempt.risk_decision,
        risk_reasons=attempt.risk_reasons,
        created_at=attempt.created_at,
        completed_at=attempt.completed_at,
    )


def _new_reference(db: Session, model, column) -> str:
    for _ in range(5):
        reference = generate_reference()
        if db.scalar(select(model.id).where(column == reference)) is None:
            return reference
    return generate_reference("AXQ")


def add_evidence(
    db: Session,
    attempt: AttendanceAttempt,
    *,
    factor: str,
    status: FactorStatus | str,
    score: float | None = None,
    reason_code: str | None = None,
    details: dict | None = None,
    provider: str | None = None,
    model_version: str | None = None,
) -> VerificationEvidence:
    evidence = VerificationEvidence(
        attempt_id=attempt.id,
        factor=factor,
        status=status.value if hasattr(status, "value") else str(status),
        score=score,
        reason_code=reason_code,
        details=details,
        provider=provider,
        model_version=model_version,
    )
    db.add(evidence)
    return evidence


def start_attempt(
    db: Session,
    *,
    token: str,
    student_id: uuid.UUID,
    settings: Settings,
    ip_address: str | None,
    user_agent: str | None,
) -> tuple[AttendanceAttempt, QrValidateResponse, list[str], str | None]:
    qr_row, session = validate_qr(db, token, settings)
    ensure_enrolled(db, session, student_id)
    record = existing_record(db, session.id, student_id)
    if record is not None:
        raise errors.conflict(
            "Attendance has already been recorded for this session.",
            "ALREADY_RECORDED",
            reference=record.reference,
            status=record.status.value,
        )
    active = db.scalar(
        select(AttendanceAttempt)
        .where(
            AttendanceAttempt.session_id == session.id,
            AttendanceAttempt.student_id == student_id,
            AttendanceAttempt.status == AttemptStatus.IN_PROGRESS,
        )
        .order_by(AttendanceAttempt.created_at.desc())
    )
    if active is not None:
        view = qr_validate_response(db, session, student_id, settings)
        return active, view, required_steps(session), next_step(active, session)

    attempt = AttendanceAttempt(
        reference=_new_reference(db, AttendanceAttempt, AttendanceAttempt.reference),
        session_id=session.id,
        student_id=student_id,
        qr_token_id=qr_row.id,
        status=AttemptStatus.IN_PROGRESS,
        qr_status=FactorStatus.PASSED,
        pin_status=FactorStatus.PENDING if session.require_pin else FactorStatus.NOT_REQUIRED,
        gps_status=GpsStatus.UNAVAILABLE,
        face_status=FactorStatus.PENDING if session.require_face else FactorStatus.NOT_REQUIRED,
        liveness_status=(
            FactorStatus.PENDING if session.require_liveness else FactorStatus.NOT_REQUIRED
        ),
        client_ip=ip_address,
        user_agent=(user_agent or "")[:300] or None,
    )
    db.add(attempt)
    db.flush()
    add_evidence(
        db,
        attempt,
        factor="qr",
        status=FactorStatus.PASSED,
        reason_code="QR_VALID",
        details={"qr_token_id": str(qr_row.id)},
    )
    attempt.current_step = next_step(attempt, session) or "finalize"
    db.commit()
    db.refresh(attempt)
    view = qr_validate_response(db, session, student_id, settings)
    return attempt, view, required_steps(session), next_step(attempt, session)


def _attempt_for_student(
    db: Session, attempt_id: uuid.UUID, student_id: uuid.UUID
) -> tuple[AttendanceAttempt, AttendanceSession]:
    attempt = db.get(AttendanceAttempt, attempt_id)
    if attempt is None or attempt.student_id != student_id:
        raise errors.not_found("Attendance attempt not found.")
    session = get_session(db, attempt.session_id)
    return attempt, session


def _ensure_attempt_open(attempt: AttendanceAttempt, session: AttendanceSession) -> None:
    if attempt.status != AttemptStatus.IN_PROGRESS:
        raise errors.conflict("This attendance attempt is already complete.", "ATTEMPT_COMPLETE")
    if session.status != SessionStatus.OPEN:
        raise errors.conflict("This attendance session is no longer open.", "SESSION_CLOSED")
    if utcnow() >= session.ends_at:
        raise errors.conflict("The attendance window has closed.", "SESSION_EXPIRED")


def submit_pin(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    student_id: uuid.UUID,
    pin: str,
    settings: Settings,
    ip_address: str | None,
) -> tuple[AttendanceAttempt, str | None]:
    attempt, session = _attempt_for_student(db, attempt_id, student_id)
    _ensure_attempt_open(attempt, session)
    if not session.require_pin:
        attempt.pin_status = FactorStatus.NOT_REQUIRED
        attempt.current_step = next_step(attempt, session) or "finalize"
        db.commit()
        return attempt, next_step(attempt, session)

    allowed, retry_after = check_rate_limit(
        db,
        key=f"pin:{attempt.id}",
        limit=settings.pin_max_attempts * 3,
        window_seconds=300,
    )
    if not allowed:
        raise errors.too_many_requests("Too many PIN attempts for this check-in.", retry_after)
    attempt.pin_attempts += 1

    if session.pin_hash is None or session.pin_expires_at is None or utcnow() > session.pin_expires_at:
        attempt.pin_status = FactorStatus.FAILED
        attempt.status = AttemptStatus.REJECTED
        attempt.completed_at = utcnow()
        add_evidence(
            db, attempt, factor="pin", status=FactorStatus.FAILED, reason_code="PIN_UNAVAILABLE"
        )
        db.commit()
        raise errors.bad_request("The PIN for this session is no longer available.", "PIN_UNAVAILABLE")

    if not verify_pin(pin, session.pin_hash):
        remaining = max(0, settings.pin_max_attempts - attempt.pin_attempts)
        audit_service.security(
            db,
            event_type="PIN_VERIFICATION_FAILED",
            severity=SecuritySeverity.LOW,
            user_id=db.get(StudentProfile, student_id).user_id if db.get(StudentProfile, student_id) else None,
            session_id=session.id,
            ip_address=ip_address,
            details={"attempt_id": str(attempt.id), "remaining": remaining},
        )
        if remaining <= 0:
            attempt.pin_status = FactorStatus.FAILED
            attempt.status = AttemptStatus.REJECTED
            attempt.completed_at = utcnow()
            add_evidence(
                db,
                attempt,
                factor="pin",
                status=FactorStatus.FAILED,
                reason_code="PIN_ATTEMPTS_EXCEEDED",
            )
            _finalize_rejected_attempt(db, attempt, session, "PIN_ATTEMPTS_EXCEEDED")
        db.commit()
        raise errors.bad_request(
            f"Incorrect PIN. {remaining} attempt(s) remaining.", "PIN_INVALID"
        )

    attempt.pin_status = FactorStatus.PASSED
    add_evidence(db, attempt, factor="pin", status=FactorStatus.PASSED, reason_code="PIN_VERIFIED")
    attempt.current_step = next_step(attempt, session) or "finalize"
    db.commit()
    db.refresh(attempt)
    return attempt, next_step(attempt, session)


def _finalize_rejected_attempt(
    db: Session, attempt: AttendanceAttempt, session: AttendanceSession, reason: str
) -> AttendanceRecord:
    record = AttendanceRecord(
        reference=_new_reference(db, AttendanceRecord, AttendanceRecord.reference),
        session_id=session.id,
        student_id=attempt.student_id,
        attempt_id=attempt.id,
        status=AttendanceStatus.REJECTED,
        classification=AttendanceClassification.INVALID,
        decision_source=DecisionSource.SYSTEM,
        decided_at=utcnow(),
        remarks=f"Rejected by verification: {reason}",
    )
    db.add(record)
    audit_service.security(
        db,
        event_type="ATTENDANCE_REJECTED",
        severity=SecuritySeverity.MEDIUM,
        session_id=session.id,
        details={"attempt_id": str(attempt.id), "reason": reason},
    )
    return record


def submit_location(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    student_id: uuid.UUID,
    payload,  # LocationRequest
    settings: Settings,
) -> tuple[AttendanceAttempt, object]:
    attempt, session = _attempt_for_student(db, attempt_id, student_id)
    _ensure_attempt_open(attempt, session)

    config = _geofence_config(db, session, settings)
    client_ts = parse_client_timestamp(payload.client_timestamp)
    evidence = evaluate_location(
        config=config,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy_m=payload.accuracy_m,
        client_timestamp=client_ts,
        server_received_at=utcnow(),
        stale_after_seconds=settings.gps_stale_after_seconds,
        permission_denied=payload.permission_denied,
        unavailable=payload.unavailable,
    )
    attempt.gps_submitted_at = utcnow()
    attempt.gps_recorded_at = client_ts
    attempt.gps_distance_m = evidence.distance_m
    attempt.gps_accuracy_m = evidence.accuracy_m
    attempt.gps_status = evidence.status
    add_evidence(
        db,
        attempt,
        factor="gps",
        status=FactorStatus.PASSED if evidence.status == GpsStatus.INSIDE_GEOFENCE else evidence.status.value,
        reason_code=evidence.reason_code,
        details={
            "latitude": payload.latitude,
            "longitude": payload.longitude,
            "accuracy_m": evidence.accuracy_m,
            "distance_m": evidence.distance_m,
            **evidence.details,
        },
    )
    attempt.current_step = next_step(attempt, session) or "finalize"
    db.commit()
    db.refresh(attempt)
    return attempt, evidence


def _geofence_config(
    db: Session, session: AttendanceSession, settings: Settings
) -> GeofenceConfig:
    if session.geofence_id is not None:
        policy = db.get(GeofencePolicy, session.geofence_id)
        if policy is not None:
            return GeofenceConfig(
                center_latitude=policy.center_latitude,
                center_longitude=policy.center_longitude,
                radius_m=policy.radius_m,
                max_accuracy_m=policy.max_accuracy_m,
            )
    classroom = db.get(Classroom, session.classroom_id)
    if classroom is not None:
        return GeofenceConfig(
            center_latitude=classroom.latitude,
            center_longitude=classroom.longitude,
            radius_m=classroom.default_radius_m,
            max_accuracy_m=classroom.max_accuracy_m,
        )
    return GeofenceConfig(
        center_latitude=0.0,
        center_longitude=0.0,
        radius_m=settings.default_geofence_radius_m,
        max_accuracy_m=settings.default_max_gps_accuracy_m,
    )


def _active_biometric(db: Session, student_id: uuid.UUID) -> bool:
    from app.services.biometrics import has_active_enrollment

    return has_active_enrollment(db, student_id)


def submit_face(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    student_id: uuid.UUID,
    image: bytes | None,
    content_type: str,
    settings: Settings,
) -> tuple[AttendanceAttempt, VerificationResult]:
    attempt, session = _attempt_for_student(db, attempt_id, student_id)
    _ensure_attempt_open(attempt, session)

    if not session.require_face:
        attempt.face_status = FactorStatus.NOT_REQUIRED
        attempt.current_step = next_step(attempt, session) or "finalize"
        db.commit()
        return attempt, VerificationResult(
            status=FactorStatus.NOT_REQUIRED,
            reason_code="FACE_NOT_REQUIRED",
            provider="none",
        )

    provider = get_face_provider(settings)
    if image:
        if len(image) > 5 * 1024 * 1024:
            raise errors.bad_request("The face image must be smaller than 5 MB.", "IMAGE_TOO_LARGE")
        if content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise errors.bad_request("Only JPEG, PNG or WebP images are accepted.", "UNSUPPORTED_IMAGE")

    reference_embedding = None
    enrollment_ok = _active_biometric(db, student_id)
    if provider.name == "local_opencv" and enrollment_ok:
        from app.services.biometrics import active_reference_embedding

        reference_embedding = active_reference_embedding(db, student_id, settings)

    if image is None:
        result = VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code="FACE_IMAGE_MISSING",
            provider=provider.name,
        )
    elif provider.name == "local_opencv" and (not enrollment_ok or reference_embedding is None):
        result = VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code="FACE_NOT_ENROLLED",
            provider=provider.name,
        )
    elif not provider.configured:
        result = provider.verify(
            image=image, content_type=content_type, student_reference=str(student_id)
        )
    elif provider.name != "local_opencv" and not enrollment_ok:
        result = VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code="FACE_NOT_ENROLLED",
            provider=provider.name,
        )
    else:
        try:
            result = provider.verify(
                image=image,
                content_type=content_type,
                student_reference=str(student_id),
                reference_embedding=reference_embedding,
            )
        except Exception:  # noqa: BLE001 - provider boundary
            result = VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="FACE_PROVIDER_EXCEPTION",
                provider=provider.name,
            )

    attempt.face_status = result.status
    add_evidence(
        db,
        attempt,
        factor="face",
        status=result.status,
        score=result.score,
        reason_code=result.reason_code,
        details=result.details,
        provider=result.provider,
        model_version=result.model_version,
    )
    attempt.current_step = next_step(attempt, session) or "finalize"
    db.commit()
    db.refresh(attempt)
    return attempt, result


def submit_liveness(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    student_id: uuid.UUID,
    image: bytes | None,
    content_type: str,
    settings: Settings,
) -> tuple[AttendanceAttempt, VerificationResult]:
    attempt, session = _attempt_for_student(db, attempt_id, student_id)
    _ensure_attempt_open(attempt, session)

    if not session.require_liveness:
        attempt.liveness_status = FactorStatus.NOT_REQUIRED
        attempt.current_step = next_step(attempt, session) or "finalize"
        db.commit()
        return attempt, VerificationResult(
            status=FactorStatus.NOT_REQUIRED,
            reason_code="LIVENESS_NOT_REQUIRED",
            provider="none",
        )

    provider = get_liveness_provider(settings)
    if image and content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise errors.bad_request("Only JPEG, PNG or WebP images are accepted.", "UNSUPPORTED_IMAGE")

    if image is None:
        result = VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code="LIVENESS_IMAGE_MISSING",
            provider=provider.name,
        )
    else:
        try:
            result = provider.check(image=image, content_type=content_type)
        except Exception:  # noqa: BLE001 - provider boundary
            result = VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LIVENESS_PROVIDER_EXCEPTION",
                provider=provider.name,
            )

    attempt.liveness_status = result.status
    add_evidence(
        db,
        attempt,
        factor="liveness",
        status=result.status,
        score=result.score,
        reason_code=result.reason_code,
        details=result.details,
        provider=result.provider,
        model_version=result.model_version,
    )
    attempt.current_step = next_step(attempt, session) or "finalize"
    db.commit()
    db.refresh(attempt)
    return attempt, result


def _finalize_response(record: AttendanceRecord, attempt: AttendanceAttempt) -> FinalizeResponse:
    return FinalizeResponse(
        record_id=record.id,
        reference=record.reference,
        session_id=record.session_id,
        status=record.status,
        classification=record.classification,
        decision_source=record.decision_source,
        decision=attempt.risk_decision or RiskDecision.REJECTED,
        risk_score=attempt.risk_score,
        reasons=attempt.risk_reasons or [],
        check_in_at=record.check_in_at,
    )


def finalize_attempt(
    db: Session,
    *,
    attempt_id: uuid.UUID,
    student_id: uuid.UUID,
    settings: Settings,
) -> FinalizeResponse:
    attempt, session = _attempt_for_student(db, attempt_id, student_id)

    if attempt.status != AttemptStatus.IN_PROGRESS:
        record = db.scalar(select(AttendanceRecord).where(AttendanceRecord.attempt_id == attempt.id))
        if record is not None:
            return _finalize_response(record, attempt)
        raise errors.conflict("This attendance attempt is already complete.", "ATTEMPT_COMPLETE")

    now = utcnow()
    if session.status != SessionStatus.OPEN:
        raise errors.conflict("This attendance session is closed.", "SESSION_CLOSED")
    if now > session.ends_at + timedelta(seconds=30):
        session.status = SessionStatus.EXPIRED
        db.commit()
        raise errors.conflict("The attendance window has closed.", "SESSION_EXPIRED")

    pending = next_step(attempt, session)
    if pending is not None:
        raise errors.bad_request(
            "Required verification steps are still pending.", "VERIFICATION_PENDING", next_step=pending
        )

    risk = evaluate_risk(
        RiskInput(
            required=RequiredFactors(
                pin=session.require_pin,
                geofence=session.require_geofence,
                face=session.require_face,
                liveness=session.require_liveness,
            ),
            qr_status=attempt.qr_status,
            pin_status=attempt.pin_status,
            gps_status=attempt.gps_status,
            face_status=attempt.face_status,
            liveness_status=attempt.liveness_status,
            allow_review_outside_geofence=session.allow_review_outside_geofence,
            duplicate_attendance=existing_record(db, session.id, student_id) is not None,
        )
    )

    if risk.decision == RiskDecision.ACCEPTED:
        status = AttendanceStatus.PRESENT
        classification = AttendanceClassification.FULL
    elif risk.decision == RiskDecision.REVIEW_REQUIRED:
        status = AttendanceStatus.REVIEW_REQUIRED
        classification = AttendanceClassification.PENDING_REVIEW
    else:
        status = AttendanceStatus.REJECTED
        classification = AttendanceClassification.INVALID

    attempt.risk_decision = risk.decision
    attempt.risk_score = risk.score
    attempt.risk_reasons = risk.reasons_dict()
    attempt.status = (
        AttemptStatus.ACCEPTED
        if risk.decision == RiskDecision.ACCEPTED
        else AttemptStatus.REVIEW_REQUIRED
        if risk.decision == RiskDecision.REVIEW_REQUIRED
        else AttemptStatus.REJECTED
    )
    attempt.completed_at = now

    record = AttendanceRecord(
        reference=_new_reference(db, AttendanceRecord, AttendanceRecord.reference),
        session_id=session.id,
        student_id=student_id,
        attempt_id=attempt.id,
        status=status,
        classification=classification,
        decision_source=DecisionSource.SYSTEM,
        decided_at=now,
        check_in_at=now if risk.decision == RiskDecision.ACCEPTED else None,
        remarks="; ".join(r.code for r in risk.reasons) or None,
    )
    db.add(record)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = existing_record(db, session.id, student_id)
        if existing is None:
            raise errors.conflict("Attendance could not be recorded.", "RECORD_CONFLICT")
        current_attempt = db.get(AttendanceAttempt, attempt.id)
        return FinalizeResponse(
            record_id=existing.id,
            reference=existing.reference,
            session_id=existing.session_id,
            status=existing.status,
            classification=existing.classification,
            decision_source=existing.decision_source,
            decision=(current_attempt.risk_decision if current_attempt else None)
            or RiskDecision.REVIEW_REQUIRED,
            risk_score=current_attempt.risk_score if current_attempt else 0,
            reasons=(current_attempt.risk_reasons if current_attempt else None) or [],
            check_in_at=existing.check_in_at,
        )

    if risk.decision == RiskDecision.REVIEW_REQUIRED:
        from app.models import ReviewRequest, ReviewStatus

        db.add(
            ReviewRequest(
                record_id=record.id,
                attempt_id=attempt.id,
                student_id=student_id,
                session_id=session.id,
                reason="Automatic review: " + ", ".join(r.code for r in risk.reasons if r.severity != "info"),
                status=ReviewStatus.OPEN,
            )
        )
    if risk.decision == RiskDecision.REJECTED:
        audit_service.security(
            db,
            event_type="ATTENDANCE_REJECTED",
            severity=SecuritySeverity.MEDIUM,
            session_id=session.id,
            details={
                "attempt_id": str(attempt.id),
                "reasons": [r.code for r in risk.reasons if r.severity == "block"],
            },
        )

    db.commit()
    db.refresh(record)
    db.refresh(attempt)
    return _finalize_response(record, attempt)


# ---------------------------------------------------------------------------
# Teacher live view
# ---------------------------------------------------------------------------
def live_session(
    db: Session,
    *,
    session: AttendanceSession,
    actor_user_id: uuid.UUID,
    settings: Settings,
) -> LiveSessionResponse:
    qr = None
    if session.status == SessionStatus.OPEN and utcnow() < session.ends_at:
        try:
            row = current_qr(db, session, actor_user_id, settings)
            qr = qr_out(row, settings, session.qr_refresh_seconds)
        except errors.ApiError:
            qr = None

    rows = db.execute(
        select(AttendanceAttempt, StudentProfile, User)
        .join(StudentProfile, StudentProfile.id == AttendanceAttempt.student_id)
        .join(User, User.id == StudentProfile.user_id)
        .where(AttendanceAttempt.session_id == session.id)
        .order_by(AttendanceAttempt.created_at.desc())
        .limit(50)
    ).all()
    recent = [
        LiveAttemptOut(
            attempt_id=attempt.id,
            reference=attempt.reference,
            student_name=user.full_name,
            roll_number=student.roll_number,
            status=attempt.status,
            current_step=attempt.current_step,
            gps_status=attempt.gps_status,
            face_status=attempt.face_status,
            liveness_status=attempt.liveness_status,
            risk_decision=attempt.risk_decision,
            created_at=attempt.created_at,
        )
        for attempt, student, user in rows
    ]
    remaining = max(0, int((session.ends_at - utcnow()).total_seconds()))
    return LiveSessionResponse(
        session=session_out(db, session),
        qr=qr,
        seconds_remaining=remaining,
        recent_attempts=recent,
    )
