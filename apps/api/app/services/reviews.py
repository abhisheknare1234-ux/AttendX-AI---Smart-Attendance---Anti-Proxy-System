"""Teacher review queue and attendance corrections."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.security import generate_reference
from app.core.timeutil import utcnow
from app.models import (
    AttendanceClassification,
    AttendanceCorrection,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    AttemptStatus,
    AttendanceAttempt,
    DecisionSource,
    ReviewRequest,
    ReviewStatus,
    SchoolClass,
    StudentProfile,
    Subject,
    TeacherProfile,
    User,
)
from app.schemas.attendance import ReviewOut
from app.services import audit as audit_service


def _review_out(db: Session, review: ReviewRequest) -> ReviewOut:
    session = db.get(AttendanceSession, review.session_id)
    subject = db.get(Subject, session.subject_id) if session else None
    school_class = db.get(SchoolClass, session.class_id) if session else None
    student = db.get(StudentProfile, review.student_id)
    student_user = db.get(User, student.user_id) if student else None
    attempt = db.get(AttendanceAttempt, review.attempt_id) if review.attempt_id else None
    record = db.get(AttendanceRecord, review.record_id) if review.record_id else None
    return ReviewOut(
        id=review.id,
        session_id=review.session_id,
        subject_name=subject.name if subject else "",
        class_name=school_class.name if school_class else "",
        student_id=review.student_id,
        student_name=student_user.full_name if student_user else "",
        roll_number=student.roll_number if student else "",
        reason=review.reason,
        status=review.status,
        attempt_reference=attempt.reference if attempt else None,
        record_reference=record.reference if record else None,
        risk_decision=attempt.risk_decision if attempt else None,
        risk_score=attempt.risk_score if attempt else None,
        risk_reasons=attempt.risk_reasons if attempt else None,
        session_starts_at=session.starts_at if session else review.created_at,
        created_at=review.created_at,
        resolved_at=review.resolved_at,
        resolution_note=review.resolution_note,
    )


def list_reviews_for_teacher(
    db: Session, *, teacher_id: uuid.UUID, status: ReviewStatus | None = None, limit: int = 100
) -> list[ReviewOut]:
    query = (
        select(ReviewRequest)
        .join(AttendanceSession, AttendanceSession.id == ReviewRequest.session_id)
        .where(AttendanceSession.teacher_id == teacher_id)
        .order_by(ReviewRequest.created_at.desc())
        .limit(limit)
    )
    if status is not None:
        query = query.where(ReviewRequest.status == status)
    return [_review_out(db, review) for review in db.scalars(query).all()]


def list_reviews_for_student(
    db: Session, *, student_id: uuid.UUID, limit: int = 100
) -> list[ReviewOut]:
    rows = db.scalars(
        select(ReviewRequest)
        .where(ReviewRequest.student_id == student_id)
        .order_by(ReviewRequest.created_at.desc())
        .limit(limit)
    ).all()
    return [_review_out(db, review) for review in rows]


def create_student_review(
    db: Session,
    *,
    student_id: uuid.UUID,
    session_id: uuid.UUID,
    reason: str,
) -> ReviewOut:
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise errors.not_found("Attendance session not found.")
    record = db.scalar(
        select(AttendanceRecord).where(
            AttendanceRecord.session_id == session_id,
            AttendanceRecord.student_id == student_id,
        )
    )
    attempt = db.scalar(
        select(AttendanceAttempt)
        .where(
            AttendanceAttempt.session_id == session_id,
            AttendanceAttempt.student_id == student_id,
        )
        .order_by(AttendanceAttempt.created_at.desc())
    )
    if record is None and attempt is None:
        raise errors.bad_request(
            "There is no attendance attempt to review for this session.", "NO_ATTEMPT"
        )
    duplicate = db.scalar(
        select(ReviewRequest).where(
            ReviewRequest.session_id == session_id,
            ReviewRequest.student_id == student_id,
            ReviewRequest.status == ReviewStatus.OPEN,
        )
    )
    if duplicate is not None:
        raise errors.conflict("A review request for this session is already open.", "REVIEW_EXISTS")
    review = ReviewRequest(
        record_id=record.id if record else None,
        attempt_id=attempt.id if attempt else None,
        student_id=student_id,
        session_id=session_id,
        reason=reason.strip(),
    )
    db.add(review)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=db.get(StudentProfile, student_id).user_id,
        action="REVIEW_REQUESTED",
        entity_type="review_request",
        entity_id=review.id,
        details={"session_id": str(session_id)},
    )
    db.commit()
    db.refresh(review)
    return _review_out(db, review)


def resolve_review(
    db: Session,
    *,
    review_id: uuid.UUID,
    teacher_id: uuid.UUID,
    teacher_user_id: uuid.UUID,
    decision: str,
    note: str,
    mark_present: bool | None,
) -> ReviewOut:
    review = db.get(ReviewRequest, review_id)
    if review is None:
        raise errors.not_found("Review request not found.")
    session = db.get(AttendanceSession, review.session_id)
    if session is None or session.teacher_id != teacher_id:
        raise errors.forbidden("This review does not belong to one of your sessions.")
    if review.status != ReviewStatus.OPEN:
        raise errors.conflict("This review has already been resolved.", "REVIEW_RESOLVED")

    record = db.get(AttendanceRecord, review.record_id) if review.record_id else None
    if record is None:
        record = db.scalar(
            select(AttendanceRecord).where(
                AttendanceRecord.session_id == review.session_id,
                AttendanceRecord.student_id == review.student_id,
            )
        )

    now = utcnow()
    approved = decision == "approved"
    present = approved if mark_present is None else bool(mark_present)
    new_status = AttendanceStatus.PRESENT if present else AttendanceStatus.ABSENT
    new_classification = (
        AttendanceClassification.FULL if present else AttendanceClassification.ABSENT
    )

    if record is None:
        record = AttendanceRecord(
            reference=generate_reference(),
            session_id=review.session_id,
            student_id=review.student_id,
            attempt_id=review.attempt_id,
            status=new_status,
            classification=new_classification,
            decision_source=DecisionSource.TEACHER,
            decided_by_id=teacher_user_id,
            decided_at=now,
            check_in_at=now if present else None,
            remarks=f"Teacher review: {note.strip()}",
        )
        db.add(record)
        db.flush()
        review.record_id = record.id
        old_status = None
        old_classification = None
    else:
        old_status = record.status
        old_classification = record.classification
        record.status = new_status
        record.classification = new_classification
        record.decision_source = DecisionSource.TEACHER
        record.decided_by_id = teacher_user_id
        record.decided_at = now
        record.check_in_at = now if present else record.check_in_at
        record.remarks = f"Teacher review: {note.strip()}"
        db.add(
            AttendanceCorrection(
                record_id=record.id,
                actor_user_id=teacher_user_id,
                old_status=old_status,
                new_status=new_status,
                old_classification=old_classification,
                new_classification=new_classification,
                reason=note.strip(),
            )
        )

    if review.attempt_id is not None:
        attempt = db.get(AttendanceAttempt, review.attempt_id)
        if attempt is not None and attempt.status == AttemptStatus.REVIEW_REQUIRED:
            attempt.status = AttemptStatus.ACCEPTED if present else AttemptStatus.REJECTED
            attempt.current_step = "complete"

    review.status = ReviewStatus.APPROVED if approved else ReviewStatus.REJECTED
    review.resolved_by_id = teacher_user_id
    review.resolution_note = note.strip()
    review.resolved_at = now

    audit_service.audit(
        db,
        actor_user_id=teacher_user_id,
        action="REVIEW_RESOLVED",
        entity_type="review_request",
        entity_id=review.id,
        details={
            "decision": decision,
            "mark_present": present,
            "session_id": str(review.session_id),
            "record_id": str(record.id),
        },
    )
    db.commit()
    db.refresh(review)
    return _review_out(db, review)


def correct_record(
    db: Session,
    *,
    record_id: uuid.UUID,
    teacher_id: uuid.UUID,
    teacher_user_id: uuid.UUID,
    new_status: AttendanceStatus,
    new_classification: AttendanceClassification | None,
    reason: str,
) -> AttendanceRecord:
    record = db.get(AttendanceRecord, record_id)
    if record is None:
        raise errors.not_found("Attendance record not found.")
    session = db.get(AttendanceSession, record.session_id)
    if session is None or session.teacher_id != teacher_id:
        raise errors.forbidden("This record does not belong to one of your sessions.")
    old_status = record.status
    old_classification = record.classification
    record.status = new_status
    if new_classification is not None:
        record.classification = new_classification
    record.decision_source = DecisionSource.TEACHER
    record.decided_by_id = teacher_user_id
    record.decided_at = utcnow()
    record.remarks = reason.strip()
    db.add(
        AttendanceCorrection(
            record_id=record.id,
            actor_user_id=teacher_user_id,
            old_status=old_status,
            new_status=new_status,
            old_classification=old_classification,
            new_classification=new_classification or old_classification,
            reason=reason.strip(),
        )
    )
    audit_service.audit(
        db,
        actor_user_id=teacher_user_id,
        action="ATTENDANCE_CORRECTED",
        entity_type="attendance_record",
        entity_id=record.id,
        details={
            "old_status": old_status.value,
            "new_status": new_status.value,
            "reason": reason.strip(),
        },
    )
    db.commit()
    db.refresh(record)
    return record
