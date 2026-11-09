"""Student endpoints: dashboard, history, subjects, reviews and profile."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import AuthContext, require_csrf, require_student_profile
from app.schemas.accounts import UserOut
from app.schemas.attendance import (
    AttendanceHistoryItem,
    ReviewCreateRequest,
    ReviewOut,
    StudentDashboardResponse,
    SubjectAttendanceSummary,
)
from app.services import reports as report_service
from app.services import reviews as review_service
from app.services.users import user_out

router = APIRouter(prefix="/student", tags=["student"], dependencies=[Depends(require_csrf)])


@router.get("/dashboard", response_model=StudentDashboardResponse)
def role_dashboard(
    auth: AuthContext = Depends(require_student_profile), db: Session = Depends(get_db)
):
    return report_service.student_dashboard(db, student_id=auth.student_id)


@router.get("/attendance", response_model=list[AttendanceHistoryItem])
def attendance_history(
    limit: int = Query(default=100, ge=1, le=500),
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
):
    return report_service.student_history(db, student_id=auth.student_id, limit=limit)


@router.get("/subjects", response_model=list[SubjectAttendanceSummary])
def subjects(
    auth: AuthContext = Depends(require_student_profile), db: Session = Depends(get_db)
):
    return report_service.student_subject_summaries(db, student_id=auth.student_id)


@router.get("/reviews", response_model=list[ReviewOut])
def role_reviews(
    auth: AuthContext = Depends(require_student_profile), db: Session = Depends(get_db)
):
    return review_service.list_reviews_for_student(db, student_id=auth.student_id)


@router.post("/review-requests", response_model=ReviewOut, status_code=201)
def create_review(
    payload: ReviewCreateRequest,
    auth: AuthContext = Depends(require_student_profile),
    db: Session = Depends(get_db),
):
    return review_service.create_student_review(
        db, student_id=auth.student_id, session_id=payload.session_id, reason=payload.reason
    )


@router.get("/profile", response_model=UserOut)
def role_profile(
    auth: AuthContext = Depends(require_student_profile), db: Session = Depends(get_db)
):
    return user_out(db, auth.user)
