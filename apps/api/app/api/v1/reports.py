"""Attendance reports and CSV export."""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.db import get_db
from app.core.deps import AuthContext, require_csrf, require_staff
from app.models import TeacherAssignment
from app.schemas.attendance import AttendanceReportResponse, ReportRowOut
from app.services import audit as audit_service
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(require_csrf)])


def _teacher_class_ids(db: Session, teacher_id: uuid.UUID) -> set[uuid.UUID]:
    return {
        item.class_id
        for item in db.scalars(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher_id,
                TeacherAssignment.is_active.is_(True),
            )
        ).all()
    }


def _scope(
    db: Session,
    auth: AuthContext,
    class_id: uuid.UUID | None,
) -> list[uuid.UUID | None]:
    if auth.role.value != "teacher":
        return [class_id]
    allowed = _teacher_class_ids(db, auth.teacher_id)
    if class_id is not None:
        if class_id not in allowed:
            raise errors.forbidden("You are not assigned to this class.")
        return [class_id]
    return sorted(allowed) or [None]


@router.get("/attendance", response_model=AttendanceReportResponse)
def attendance_report(
    class_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    auth: AuthContext = Depends(require_staff),
    db: Session = Depends(get_db),
):
    scopes = _scope(db, auth, class_id)
    if auth.role.value == "teacher" and len(scopes) == 1 and scopes[0] is None:
        raise errors.bad_request("No classes are assigned to you.", "NO_CLASSES")
    reports = [
        report_service.attendance_report(
            db,
            class_id=scope,
            subject_id=subject_id,
            date_from=date_from,
            date_to=date_to,
        )
        for scope in scopes
    ]
    if len(reports) == 1:
        return reports[0]
    rows: list[ReportRowOut] = [row for report in reports for row in report.rows]
    percentages = [row.attendance_percentage for row in rows if row.attendance_percentage is not None]
    return AttendanceReportResponse(
        generated_at=reports[0].generated_at,
        filters=reports[0].filters,
        totals={
            "students": len({row.student_id for row in rows}),
            "sessions": sum(report.totals.get("sessions", 0) for report in reports),
            "present": sum(report.totals.get("present", 0) for report in reports),
            "average_percentage": round(sum(percentages) / len(percentages), 1) if percentages else None,
        },
        rows=rows,
    )


@router.get("/export")
def export_report(
    class_id: uuid.UUID | None = Query(default=None),
    subject_id: uuid.UUID | None = Query(default=None),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    auth: AuthContext = Depends(require_staff),
    db: Session = Depends(get_db),
):
    scopes = _scope(db, auth, class_id)
    merged: list[ReportRowOut] = []
    for scope in scopes:
        report = report_service.attendance_report(
            db,
            class_id=scope,
            subject_id=subject_id,
            date_from=date_from,
            date_to=date_to,
        )
        merged.extend(report.rows)
    csv_text = report_service.report_to_csv(
        AttendanceReportResponse(
            generated_at=report_service.datetime.now(report_service.timezone.utc),
            filters={},
            totals={},
            rows=merged,
        )
    )
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="REPORT_EXPORTED",
        entity_type="attendance_report",
        details={
            "class_id": str(class_id) if class_id else None,
            "subject_id": str(subject_id) if subject_id else None,
            "rows": len(merged),
        },
    )
    db.commit()
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="attendx-attendance-report.csv"'},
    )
