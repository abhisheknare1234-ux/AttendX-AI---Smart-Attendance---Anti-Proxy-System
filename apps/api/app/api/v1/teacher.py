"""Teacher endpoints: dashboard, assigned academics, sessions, live view, reviews."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.core.deps import AuthContext, require_csrf, require_teacher_profile
from app.core.security import generate_pin, hash_pin
from app.core.timeutil import utcnow
from app.models import (
    AttendancePolicy,
    AttendanceRecord,
    AttendanceSession,
    ClassEnrollment,
    EnrollmentStatus,
    ReviewStatus,
    SchoolClass,
    SessionStatus,
    StudentProfile,
    Subject,
    TeacherAssignment,
    User,
)
from app.schemas.attendance import (
    CorrectionRequest,
    LiveSessionResponse,
    OpenSessionResponse,
    QrOut,
    ResolveReviewRequest,
    ReviewOut,
    SessionCreateRequest,
    SessionOut,
    TeacherDashboardResponse,
)
from app.schemas.accounts import UserOut
from app.services import audit as audit_service
from app.services import attendance as attendance_service
from app.services import reports as report_service
from app.services import reviews as review_service
from app.services.users import user_out

router = APIRouter(prefix="/teacher", tags=["teacher"], dependencies=[Depends(require_csrf)])


def _owned_session(
    db: Session, session_id: uuid.UUID, teacher_id: uuid.UUID
) -> AttendanceSession:
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise errors.not_found("Attendance session not found.")
    if session.teacher_id != teacher_id:
        raise errors.forbidden("This session does not belong to you.")
    return session


@router.get("/dashboard", response_model=TeacherDashboardResponse)
def role_dashboard(
    auth: AuthContext = Depends(require_teacher_profile), db: Session = Depends(get_db)
):
    return report_service.teacher_dashboard(
        db, teacher_id=auth.teacher_id, teacher_user_id=auth.user.id
    )


@router.get("/profile", response_model=UserOut)
def role_profile(auth: AuthContext = Depends(require_teacher_profile), db: Session = Depends(get_db)):
    return user_out(db, auth.user)


@router.get("/classes")
def my_classes(
    auth: AuthContext = Depends(require_teacher_profile), db: Session = Depends(get_db)
):
    assignments = db.scalars(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == auth.teacher_id,
            TeacherAssignment.is_active.is_(True),
        )
    ).all()
    class_ids = sorted({item.class_id for item in assignments})
    result = []
    for class_id in class_ids:
        school_class = db.get(SchoolClass, class_id)
        if school_class is None:
            continue
        subject_count = len(
            db.scalars(
                select(Subject.id).where(Subject.class_id == class_id, Subject.is_active.is_(True))
            ).all()
        )
        student_count = db.scalar(
            select(func.count(ClassEnrollment.id)).where(
                ClassEnrollment.class_id == class_id,
                ClassEnrollment.status == EnrollmentStatus.ACTIVE,
            )
        ) or 0
        result.append(
            {
                "id": str(school_class.id),
                "code": school_class.code,
                "name": school_class.name,
                "department": school_class.department,
                "year": school_class.year,
                "division": school_class.division,
                "subjects": subject_count,
                "students": student_count,
            }
        )
    return result


@router.get("/subjects")
def my_subjects(
    auth: AuthContext = Depends(require_teacher_profile), db: Session = Depends(get_db)
):
    rows = db.execute(
        select(TeacherAssignment, Subject, SchoolClass)
        .outerjoin(Subject, Subject.id == TeacherAssignment.subject_id)
        .join(SchoolClass, SchoolClass.id == TeacherAssignment.class_id)
        .where(
            TeacherAssignment.teacher_id == auth.teacher_id,
            TeacherAssignment.is_active.is_(True),
        )
        .order_by(SchoolClass.name, Subject.name)
    ).all()
    result = []
    for assignment, subject, school_class in rows:
        student_count = db.scalar(
            select(func.count(ClassEnrollment.id)).where(
                ClassEnrollment.class_id == school_class.id,
                ClassEnrollment.status == EnrollmentStatus.ACTIVE,
            )
        ) or 0
        result.append(
            {
                "assignment_id": str(assignment.id),
                "class_id": str(school_class.id),
                "class_name": school_class.name,
                "class_code": school_class.code,
                "subject_id": str(subject.id) if subject else None,
                "subject_name": subject.name if subject else "All subjects",
                "subject_code": subject.code if subject else None,
                "students": student_count,
            }
        )
    return result


@router.get("/students")
def my_students(
    class_id: uuid.UUID | None = Query(default=None),
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    assigned = {
        item.class_id
        for item in db.scalars(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == auth.teacher_id,
                TeacherAssignment.is_active.is_(True),
            )
        ).all()
    }
    if class_id is not None:
        if class_id not in assigned:
            raise errors.forbidden("You are not assigned to this class.")
        class_ids = {class_id}
    else:
        class_ids = assigned
    if not class_ids:
        return []
    rows = db.execute(
        select(StudentProfile, User, SchoolClass)
        .join(ClassEnrollment, ClassEnrollment.student_id == StudentProfile.id)
        .join(User, User.id == StudentProfile.user_id)
        .join(SchoolClass, SchoolClass.id == ClassEnrollment.class_id)
        .where(
            ClassEnrollment.class_id.in_(class_ids),
            ClassEnrollment.status == EnrollmentStatus.ACTIVE,
        )
        .order_by(User.full_name)
    ).all()
    seen: set[uuid.UUID] = set()
    result = []
    for student, user, school_class in rows:
        if student.id in seen:
            continue
        seen.add(student.id)
        result.append(
            {
                "student_id": str(student.id),
                "name": user.full_name,
                "roll_number": student.roll_number,
                "class_id": str(school_class.id),
                "class_name": school_class.name,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@router.post("/sessions", response_model=SessionOut, status_code=201)
def create_session(
    payload: SessionCreateRequest,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    session = attendance_service.create_session(
        db,
        actor_user_id=auth.user.id,
        teacher_id=auth.teacher_id,
        payload=payload,
        settings=settings,
    )
    return attendance_service.session_out(db, session)


@router.get("/sessions", response_model=list[SessionOut])
def list_sessions(
    status: SessionStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    query = (
        select(AttendanceSession)
        .where(AttendanceSession.teacher_id == auth.teacher_id)
        .order_by(AttendanceSession.starts_at.desc())
        .limit(limit)
    )
    if status is not None:
        query = query.where(AttendanceSession.status == status)
    return [attendance_service.session_out(db, item) for item in db.scalars(query).all()]


@router.get("/sessions/{session_id}", response_model=SessionOut)
def get_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    session = _owned_session(db, session_id, auth.teacher_id)
    return attendance_service.session_out(db, session)


@router.post("/sessions/{session_id}/open", response_model=OpenSessionResponse)
def open_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    session = _owned_session(db, session_id, auth.teacher_id)
    session, pin, qr_row = attendance_service.open_session(
        db, session=session, actor_user_id=auth.user.id, settings=settings
    )
    return OpenSessionResponse(
        session=attendance_service.session_out(db, session),
        pin=pin,
        pin_expires_at=session.pin_expires_at,
        qr=attendance_service.qr_out(qr_row, settings, session.qr_refresh_seconds),
    )


@router.post("/sessions/{session_id}/close", response_model=SessionOut)
def close_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    session = _owned_session(db, session_id, auth.teacher_id)
    session = attendance_service.close_session(
        db, session=session, actor_user_id=auth.user.id
    )
    return attendance_service.session_out(db, session)


@router.post("/sessions/{session_id}/qr", response_model=QrOut)
def rotate_qr(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    session = _owned_session(db, session_id, auth.teacher_id)
    row = attendance_service.rotate_qr(
        db, session=session, actor_user_id=auth.user.id, settings=settings
    )
    return attendance_service.qr_out(row, settings, session.qr_refresh_seconds)


@router.post("/sessions/{session_id}/pin/regenerate")
def regenerate_pin(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    session = _owned_session(db, session_id, auth.teacher_id)
    if session.status != SessionStatus.OPEN:
        raise errors.conflict("The session is not open.", "SESSION_NOT_OPEN")
    if utcnow() >= session.ends_at:
        raise errors.bad_request("The attendance window has closed.", "WINDOW_CLOSED")
    pin = generate_pin(settings.pin_length)
    session.pin_hash = hash_pin(pin)
    session.pin_expires_at = session.ends_at
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="SESSION_PIN_REGENERATED",
        entity_type="attendance_session",
        entity_id=session.id,
        details={},
    )
    db.commit()
    return {"pin": pin, "pin_expires_at": session.pin_expires_at}


@router.get("/sessions/{session_id}/live", response_model=LiveSessionResponse)
def live(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    session = _owned_session(db, session_id, auth.teacher_id)
    return attendance_service.live_session(
        db, session=session, actor_user_id=auth.user.id, settings=settings
    )


# ---------------------------------------------------------------------------
# Reviews and corrections
# ---------------------------------------------------------------------------
@router.get("/reviews", response_model=list[ReviewOut])
def role_reviews(
    status: ReviewStatus | None = Query(default=ReviewStatus.OPEN),
    limit: int = Query(default=100, ge=1, le=300),
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    return review_service.list_reviews_for_teacher(
        db, teacher_id=auth.teacher_id, status=status, limit=limit
    )


@router.post("/reviews/{review_id}/resolve", response_model=ReviewOut)
def resolve_review(
    review_id: uuid.UUID,
    payload: ResolveReviewRequest,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    return review_service.resolve_review(
        db,
        review_id=review_id,
        teacher_id=auth.teacher_id,
        teacher_user_id=auth.user.id,
        decision=payload.decision,
        note=payload.note,
        mark_present=payload.mark_present,
    )


@router.post("/records/{record_id}/correction")
def correct_record(
    record_id: uuid.UUID,
    payload: CorrectionRequest,
    auth: AuthContext = Depends(require_teacher_profile),
    db: Session = Depends(get_db),
):
    record = review_service.correct_record(
        db,
        record_id=record_id,
        teacher_id=auth.teacher_id,
        teacher_user_id=auth.user.id,
        new_status=payload.new_status,
        new_classification=payload.new_classification,
        reason=payload.reason,
    )
    return {
        "record_id": str(record.id),
        "reference": record.reference,
        "status": record.status.value,
        "classification": record.classification.value,
    }
