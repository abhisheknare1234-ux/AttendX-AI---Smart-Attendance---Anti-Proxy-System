"""Dashboards, attendance history and reports."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AttendanceAttempt,
    AttendanceClassification,
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
    AttemptStatus,
    ClassEnrollment,
    DecisionSource,
    EnrollmentStatus,
    ReviewRequest,
    ReviewStatus,
    SchoolClass,
    SessionStatus,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
    User,
)
from app.schemas.accounts import UserOut
from app.schemas.attendance import (
    ActiveSessionSummary,
    AttendanceHistoryItem,
    AttendanceReportResponse,
    ReportRowOut,
    StudentDashboardResponse,
    SubjectAttendanceSummary,
    TeacherDashboardResponse,
)
from app.services.attendance import session_out
from app.services.reviews import list_reviews_for_teacher


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def student_enrolled_class_ids(db: Session, student_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        db.scalars(
            select(ClassEnrollment.class_id).where(
                ClassEnrollment.student_id == student_id,
                ClassEnrollment.status == EnrollmentStatus.ACTIVE,
            )
        ).all()
    )


def _held_session_filter():
    return (AttendanceSession.status.in_([SessionStatus.OPEN, SessionStatus.CLOSED, SessionStatus.EXPIRED])) & (
        AttendanceSession.starts_at <= func.current_timestamp()
    )


def student_history(
    db: Session, *, student_id: uuid.UUID, limit: int = 50
) -> list[AttendanceHistoryItem]:
    rows = db.execute(
        select(AttendanceRecord, AttendanceSession, Subject, SchoolClass)
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .join(Subject, Subject.id == AttendanceSession.subject_id)
        .join(SchoolClass, SchoolClass.id == AttendanceSession.class_id)
        .where(AttendanceRecord.student_id == student_id)
        .order_by(AttendanceSession.starts_at.desc())
        .limit(limit)
    ).all()
    return [
        AttendanceHistoryItem(
            record_id=record.id,
            reference=record.reference,
            session_id=record.session_id,
            subject_name=subject.name,
            subject_code=subject.code,
            class_name=school_class.name,
            status=record.status,
            classification=record.classification,
            decision_source=record.decision_source,
            check_in_at=record.check_in_at,
            session_starts_at=session.starts_at,
            session_ends_at=session.ends_at,
        )
        for record, session, subject, school_class in rows
    ]


def student_subject_summaries(
    db: Session, *, student_id: uuid.UUID
) -> list[SubjectAttendanceSummary]:
    class_ids = student_enrolled_class_ids(db, student_id)
    if not class_ids:
        return []
    now = datetime.now(timezone.utc)
    subjects = db.scalars(
        select(Subject)
        .where(Subject.class_id.in_(class_ids), Subject.is_active.is_(True))
        .order_by(Subject.name)
    ).all()
    summaries: list[SubjectAttendanceSummary] = []
    for subject in subjects:
        school_class = db.get(SchoolClass, subject.class_id)
        held = db.scalar(
            select(func.count(func.distinct(AttendanceSession.id))).where(
                AttendanceSession.subject_id == subject.id,
                AttendanceSession.status != SessionStatus.CANCELLED,
                AttendanceSession.starts_at <= now,
            )
        ) or 0
        present = db.scalar(
            select(func.count(func.distinct(AttendanceRecord.id)))
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceSession.subject_id == subject.id,
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        ) or 0
        summaries.append(
            SubjectAttendanceSummary(
                subject_id=subject.id,
                subject_name=subject.name,
                subject_code=subject.code,
                class_name=school_class.name if school_class else "",
                sessions=held,
                present=present,
                percentage=round(present / held * 100, 1) if held else None,
            )
        )
    return summaries


def _active_sessions_for_student(db: Session, student_id: uuid.UUID) -> list[ActiveSessionSummary]:
    class_ids = student_enrolled_class_ids(db, student_id)
    if not class_ids:
        return []
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(AttendanceSession, Subject, SchoolClass)
        .join(Subject, Subject.id == AttendanceSession.subject_id)
        .join(SchoolClass, SchoolClass.id == AttendanceSession.class_id)
        .where(
            AttendanceSession.class_id.in_(class_ids),
            AttendanceSession.status == SessionStatus.OPEN,
            AttendanceSession.ends_at > now,
        )
        .order_by(AttendanceSession.ends_at)
    ).all()
    return [
        ActiveSessionSummary(
            session_id=session.id,
            subject_name=subject.name,
            class_name=school_class.name,
            status=session.status,
            ends_at=session.ends_at,
            seconds_remaining=max(0, int((session.ends_at - now).total_seconds())),
        )
        for session, subject, school_class in rows
    ]


def _upcoming_sessions_for_student(db: Session, student_id: uuid.UUID) -> list[ActiveSessionSummary]:
    class_ids = student_enrolled_class_ids(db, student_id)
    if not class_ids:
        return []
    now = datetime.now(timezone.utc)
    rows = db.execute(
        select(AttendanceSession, Subject, SchoolClass)
        .join(Subject, Subject.id == AttendanceSession.subject_id)
        .join(SchoolClass, SchoolClass.id == AttendanceSession.class_id)
        .where(
            AttendanceSession.class_id.in_(class_ids),
            AttendanceSession.status == SessionStatus.SCHEDULED,
            AttendanceSession.starts_at > now,
        )
        .order_by(AttendanceSession.starts_at)
        .limit(5)
    ).all()
    return [
        ActiveSessionSummary(
            session_id=session.id,
            subject_name=subject.name,
            class_name=school_class.name,
            status=session.status,
            ends_at=session.ends_at,
            seconds_remaining=max(0, int((session.starts_at - now).total_seconds())),
        )
        for session, subject, school_class in rows
    ]


def student_dashboard(db: Session, *, student_id: uuid.UUID) -> StudentDashboardResponse:
    student = db.get(StudentProfile, student_id)
    user = db.get(User, student.user_id) if student else None
    if student is None or user is None:
        from app.core import errors

        raise errors.not_found("Student profile not found.")
    class_ids = student_enrolled_class_ids(db, student_id)
    total_sessions = 0
    attended = 0
    now = datetime.now(timezone.utc)
    if class_ids:
        total_sessions = db.scalar(
            select(func.count(func.distinct(AttendanceSession.id))).where(
                AttendanceSession.class_id.in_(class_ids),
                AttendanceSession.status != SessionStatus.CANCELLED,
                AttendanceSession.starts_at <= now,
            )
        ) or 0
        attended = db.scalar(
            select(func.count(func.distinct(AttendanceRecord.id)))
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .where(
                AttendanceRecord.student_id == student_id,
                AttendanceSession.class_id.in_(class_ids),
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
        ) or 0
    pending_reviews = db.scalar(
        select(func.count(ReviewRequest.id)).where(
            ReviewRequest.student_id == student_id,
            ReviewRequest.status == ReviewStatus.OPEN,
        )
    ) or 0
    return StudentDashboardResponse(
        student_name=user.full_name,
        roll_number=student.roll_number,
        total_sessions=total_sessions,
        attended_sessions=attended,
        attendance_percentage=round(attended / total_sessions * 100, 1) if total_sessions else None,
        pending_reviews=pending_reviews,
        active_sessions=_active_sessions_for_student(db, student_id),
        upcoming_sessions=_upcoming_sessions_for_student(db, student_id),
        subjects=student_subject_summaries(db, student_id=student_id),
        recent_records=student_history(db, student_id=student_id, limit=8),
    )


def teacher_dashboard(
    db: Session, *, teacher_id: uuid.UUID, teacher_user_id: uuid.UUID
) -> TeacherDashboardResponse:
    teacher = db.get(TeacherProfile, teacher_id)
    user = db.get(User, teacher_user_id)
    assignments = db.scalars(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == teacher_id,
            TeacherAssignment.is_active.is_(True),
        )
    ).all()
    class_ids = sorted({a.class_id for a in assignments})
    subject_ids = sorted({a.subject_id for a in assignments if a.subject_id is not None})
    students_count = 0
    if class_ids:
        students_count = db.scalar(
            select(func.count(func.distinct(ClassEnrollment.student_id))).where(
                ClassEnrollment.class_id.in_(class_ids),
                ClassEnrollment.status == EnrollmentStatus.ACTIVE,
            )
        ) or 0

    now = datetime.now(timezone.utc)
    today_start, today_end = _day_bounds(now.date())

    active_sessions = db.scalar(
        select(func.count(AttendanceSession.id)).where(
            AttendanceSession.teacher_id == teacher_id,
            AttendanceSession.status == SessionStatus.OPEN,
        )
    ) or 0
    today_sessions = db.scalar(
        select(func.count(AttendanceSession.id)).where(
            AttendanceSession.teacher_id == teacher_id,
            AttendanceSession.starts_at >= today_start,
            AttendanceSession.starts_at < today_end,
        )
    ) or 0
    present_today = db.scalar(
        select(func.count(AttendanceRecord.id))
        .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
        .where(
            AttendanceSession.teacher_id == teacher_id,
            AttendanceSession.starts_at >= today_start,
            AttendanceSession.starts_at < today_end,
            AttendanceRecord.status == AttendanceStatus.PRESENT,
        )
    ) or 0
    review_pending = db.scalar(
        select(func.count(ReviewRequest.id))
        .join(AttendanceSession, AttendanceSession.id == ReviewRequest.session_id)
        .where(
            AttendanceSession.teacher_id == teacher_id,
            ReviewRequest.status == ReviewStatus.OPEN,
        )
    ) or 0
    failed_today = db.scalar(
        select(func.count(AttendanceAttempt.id))
        .join(AttendanceSession, AttendanceSession.id == AttendanceAttempt.session_id)
        .where(
            AttendanceSession.teacher_id == teacher_id,
            AttendanceAttempt.status == AttemptStatus.REJECTED,
            AttendanceAttempt.created_at >= today_start,
            AttendanceAttempt.created_at < today_end,
        )
    ) or 0

    recent_sessions = db.scalars(
        select(AttendanceSession)
        .where(AttendanceSession.teacher_id == teacher_id)
        .order_by(AttendanceSession.starts_at.desc())
        .limit(5)
    ).all()
    queue = list_reviews_for_teacher(db, teacher_id=teacher_id, status=ReviewStatus.OPEN, limit=10)

    return TeacherDashboardResponse(
        teacher_name=user.full_name if user else (teacher.designation if teacher else ""),
        classes_count=len(class_ids),
        subjects_count=len(subject_ids),
        students_count=students_count,
        active_sessions=active_sessions,
        today_sessions=today_sessions,
        present_today=present_today,
        review_pending=review_pending,
        failed_attempts_today=failed_today,
        recent_sessions=[session_out(db, s) for s in recent_sessions],
        review_queue=queue,
    )


def attendance_report(
    db: Session,
    *,
    class_id: uuid.UUID | None,
    subject_id: uuid.UUID | None,
    date_from: date | None,
    date_to: date | None,
) -> AttendanceReportResponse:
    now = datetime.now(timezone.utc)
    sessions_query = select(AttendanceSession).where(
        AttendanceSession.status != SessionStatus.CANCELLED,
        AttendanceSession.starts_at <= now,
    )
    if class_id is not None:
        sessions_query = sessions_query.where(AttendanceSession.class_id == class_id)
    if subject_id is not None:
        sessions_query = sessions_query.where(AttendanceSession.subject_id == subject_id)
    if date_from is not None:
        sessions_query = sessions_query.where(
            AttendanceSession.starts_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to is not None:
        sessions_query = sessions_query.where(
            AttendanceSession.starts_at
            < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=timezone.utc)
        )
    sessions = db.scalars(sessions_query).all()
    session_ids = [s.id for s in sessions]
    session_map = {s.id: s for s in sessions}

    class_ids = {s.class_id for s in sessions}
    if class_id is not None:
        class_ids = {class_id}
    if not class_ids:
        return AttendanceReportResponse(
            generated_at=now,
            filters={
                "class_id": str(class_id) if class_id else None,
                "subject_id": str(subject_id) if subject_id else None,
                "from": date_from.isoformat() if date_from else None,
                "to": date_to.isoformat() if date_to else None,
            },
            totals={"students": 0, "sessions": 0, "present": 0, "average_percentage": None},
            rows=[],
        )

    present_counts: dict[tuple[uuid.UUID, uuid.UUID], int] = {}
    if session_ids:
        present_rows = db.execute(
            select(
                AttendanceRecord.student_id,
                AttendanceSession.subject_id,
                func.count(AttendanceRecord.id),
            )
            .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            .where(
                AttendanceSession.id.in_(session_ids),
                AttendanceRecord.status == AttendanceStatus.PRESENT,
            )
            .group_by(AttendanceRecord.student_id, AttendanceSession.subject_id)
        ).all()
        for student_id, subj_id, count in present_rows:
            present_counts[(student_id, subj_id)] = count

    held_by_subject: dict[uuid.UUID, int] = {}
    for session in sessions:
        held_by_subject[session.subject_id] = held_by_subject.get(session.subject_id, 0) + 1

    rows: list[ReportRowOut] = []
    class_rows = db.execute(
        select(SchoolClass, StudentProfile, User, ClassEnrollment)
        .join(ClassEnrollment, ClassEnrollment.class_id == SchoolClass.id)
        .join(StudentProfile, StudentProfile.id == ClassEnrollment.student_id)
        .join(User, User.id == StudentProfile.user_id)
        .where(
            SchoolClass.id.in_(class_ids),
            ClassEnrollment.status == EnrollmentStatus.ACTIVE,
        )
        .order_by(SchoolClass.name, StudentProfile.roll_number)
    ).all()

    subjects = db.scalars(
        select(Subject).where(
            Subject.class_id.in_(class_ids),
            Subject.is_active.is_(True),
            *([Subject.id == subject_id] if subject_id is not None else []),
        )
    ).all()
    subjects_by_class: dict[uuid.UUID, list[Subject]] = {}
    for subject in subjects:
        subjects_by_class.setdefault(subject.class_id, []).append(subject)

    for school_class, student, user, _enrollment in class_rows:
        for subject in subjects_by_class.get(school_class.id, []):
            held = held_by_subject.get(subject.id, 0)
            present = present_counts.get((student.id, subject.id), 0)
            rows.append(
                ReportRowOut(
                    student_id=student.id,
                    student_name=user.full_name,
                    roll_number=student.roll_number,
                    class_name=school_class.name,
                    subject_name=subject.name,
                    sessions_held=held,
                    sessions_present=present,
                    attendance_percentage=round(present / held * 100, 1) if held else None,
                )
            )

    total_present = sum(row.sessions_present for row in rows)
    percentages = [row.attendance_percentage for row in rows if row.attendance_percentage is not None]
    return AttendanceReportResponse(
        generated_at=now,
        filters={
            "class_id": str(class_id) if class_id else None,
            "subject_id": str(subject_id) if subject_id else None,
            "from": date_from.isoformat() if date_from else None,
            "to": date_to.isoformat() if date_to else None,
        },
        totals={
            "students": len({row.student_id for row in rows}),
            "sessions": len(sessions),
            "present": total_present,
            "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else None,
        },
        rows=rows,
    )


def report_to_csv(report: AttendanceReportResponse) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "Student",
            "Roll Number",
            "Class",
            "Subject",
            "Sessions Held",
            "Sessions Present",
            "Attendance %",
        ]
    )
    for row in report.rows:
        writer.writerow(
            [
                row.student_name,
                row.roll_number,
                row.class_name,
                row.subject_name,
                row.sessions_held,
                row.sessions_present,
                "" if row.attendance_percentage is None else row.attendance_percentage,
            ]
        )
    return buffer.getvalue()
