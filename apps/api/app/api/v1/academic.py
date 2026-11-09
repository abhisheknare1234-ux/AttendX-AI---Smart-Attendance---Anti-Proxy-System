"""Shared academic read endpoints, scoped to the authenticated role."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import AuthContext, get_current_auth, require_csrf
from app.models import (
    AttendancePolicy,
    ClassEnrollment,
    Classroom,
    EnrollmentStatus,
    GeofencePolicy,
    SchoolClass,
    Subject,
    TeacherAssignment,
    UserRole,
)
from app.schemas.academic import ClassOut, ClassroomOut, GeofenceOut, PolicyOut, SubjectOut

router = APIRouter(tags=["academic"], dependencies=[Depends(require_csrf)])


@router.get("/classes", response_model=list[ClassOut])
def shared_classes(
    auth: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)
):
    query = select(SchoolClass).order_by(SchoolClass.name)
    if auth.role == UserRole.TEACHER:
        class_ids = select(TeacherAssignment.class_id).where(
            TeacherAssignment.teacher_id == auth.teacher_id,
            TeacherAssignment.is_active.is_(True),
        )
        query = query.where(SchoolClass.id.in_(class_ids))
    elif auth.role == UserRole.STUDENT:
        class_ids = select(ClassEnrollment.class_id).where(
            ClassEnrollment.student_id == auth.student_id,
            ClassEnrollment.status == EnrollmentStatus.ACTIVE,
        )
        query = query.where(SchoolClass.id.in_(class_ids))
    classes = db.scalars(query).all()
    return [ClassOut.model_validate(item) for item in classes]


@router.get("/subjects", response_model=list[SubjectOut])
def shared_subjects(
    class_id: uuid.UUID | None = Query(default=None),
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    query = select(Subject, SchoolClass).join(SchoolClass, SchoolClass.id == Subject.class_id)
    if class_id is not None:
        query = query.where(Subject.class_id == class_id)
    if auth.role == UserRole.TEACHER:
        class_ids = select(TeacherAssignment.class_id).where(
            TeacherAssignment.teacher_id == auth.teacher_id,
            TeacherAssignment.is_active.is_(True),
        )
        query = query.where(Subject.class_id.in_(class_ids))
    elif auth.role == UserRole.STUDENT:
        class_ids = select(ClassEnrollment.class_id).where(
            ClassEnrollment.student_id == auth.student_id,
            ClassEnrollment.status == EnrollmentStatus.ACTIVE,
        )
        query = query.where(Subject.class_id.in_(class_ids))
    rows = db.execute(query.order_by(Subject.name)).all()
    return [
        SubjectOut(
            id=subject.id,
            code=subject.code,
            name=subject.name,
            class_id=subject.class_id,
            class_code=school_class.code,
            class_name=school_class.name,
            credits=subject.credits,
            is_active=subject.is_active,
        )
        for subject, school_class in rows
    ]


@router.get("/classrooms", response_model=list[ClassroomOut])
def shared_classrooms(
    auth: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)
):
    rooms = db.scalars(
        select(Classroom).where(Classroom.is_active.is_(True)).order_by(Classroom.name)
    ).all()
    return [ClassroomOut.model_validate(room) for room in rooms]


@router.get("/geofences", response_model=list[GeofenceOut])
def shared_geofences(
    auth: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)
):
    if auth.role == UserRole.STUDENT:
        return []
    fences = db.scalars(
        select(GeofencePolicy).where(GeofencePolicy.is_active.is_(True)).order_by(GeofencePolicy.name)
    ).all()
    return [GeofenceOut.model_validate(item) for item in fences]


@router.get("/policies", response_model=list[PolicyOut])
def shared_policies(
    auth: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)
):
    if auth.role == UserRole.STUDENT:
        return []
    policies = db.scalars(select(AttendancePolicy).order_by(AttendancePolicy.name)).all()
    return [PolicyOut.model_validate(item) for item in policies]
