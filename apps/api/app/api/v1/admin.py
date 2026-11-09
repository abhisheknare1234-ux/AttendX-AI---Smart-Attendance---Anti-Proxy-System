"""Administrator endpoints: accounts, academic configuration, policies, audit and imports."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core import errors
from app.core.db import get_db
from app.core.deps import AuthContext, require_admin, require_csrf
from app.core.security import hash_password, password_problem
from app.models import (
    AttendancePolicy,
    AuditEvent,
    ClassEnrollment,
    Classroom,
    EnrollmentStatus,
    GeofencePolicy,
    SchoolClass,
    SecurityEvent,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
    User,
    UserRole,
    UserStatus,
)
from app.schemas.academic import (
    AssignmentCreateRequest,
    AssignmentOut,
    ClassCreateRequest,
    ClassOut,
    ClassroomCreateRequest,
    ClassroomOut,
    ClassroomUpdateRequest,
    ClassUpdateRequest,
    EnrollmentBulkResponse,
    EnrollmentCreateRequest,
    EnrollmentOut,
    GeofenceCreateRequest,
    GeofenceOut,
    PolicyCreateRequest,
    PolicyOut,
    PolicyUpdateRequest,
    SubjectCreateRequest,
    SubjectOut,
    SubjectUpdateRequest,
)
from app.schemas.accounts import (
    AuditEventOut,
    ImportCommitResponse,
    ImportPreviewResponse,
    ProvisionedUserResponse,
    SecurityEventOut,
    StudentCreateRequest,
    TeacherCreateRequest,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
)
from app.services import audit as audit_service
from app.services import import_csv
from app.services.users import (
    provision_admin,
    provision_student,
    provision_teacher,
    user_out,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_csrf)])


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
@router.get("/users", response_model=list[UserOut])
def list_users(
    q: str | None = Query(default=None, max_length=120),
    role: UserRole | None = Query(default=None),
    status: UserStatus | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100000),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(User).order_by(User.created_at.desc()).limit(limit).offset(offset)
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(
            or_(func.lower(User.email).like(needle), func.lower(User.full_name).like(needle))
        )
    if role is not None:
        query = query.where(User.role == role)
    if status is not None:
        query = query.where(User.status == status)
    return [user_out(db, user) for user in db.scalars(query).all()]


@router.post("/users", response_model=ProvisionedUserResponse, status_code=201)
def create_admin_user(
    payload: UserCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.role != UserRole.ADMIN:
        raise errors.bad_request(
            "Use the students or teachers endpoints to provision academic accounts.",
            "INVALID_ROLE",
        )
    user, temporary = provision_admin(
        db,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        actor_user_id=auth.user.id,
    )
    db.commit()
    db.refresh(user)
    return ProvisionedUserResponse(user=user_out(db, user), temporary_password=temporary)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise errors.not_found("User not found.")
    if user.id == auth.user.id and payload.status is not None and payload.status != UserStatus.ACTIVE:
        raise errors.bad_request("You cannot disable your own account.", "SELF_DISABLE")
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.status is not None:
        user.status = payload.status
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password
    if payload.new_password is not None:
        problem = password_problem(payload.new_password)
        if problem:
            raise errors.bad_request(problem, "WEAK_PASSWORD")
        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = True
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="USER_UPDATED",
        entity_type="user",
        entity_id=user.id,
        details={"fields": sorted(payload.model_dump(exclude_none=True).keys())},
    )
    db.commit()
    db.refresh(user)
    return user_out(db, user)


@router.get("/students", response_model=list[UserOut])
def list_students(
    q: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=100, ge=1, le=300),
    offset: int = Query(default=0, ge=0, le=100000),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = (
        select(User)
        .join(StudentProfile, StudentProfile.user_id == User.id)
        .where(User.role == UserRole.STUDENT)
        .order_by(User.full_name)
        .limit(limit)
        .offset(offset)
    )
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(User.full_name).like(needle),
                func.lower(User.email).like(needle),
                func.lower(StudentProfile.roll_number).like(needle),
            )
        )
    return [user_out(db, user) for user in db.scalars(query).all()]


@router.post("/students", response_model=ProvisionedUserResponse, status_code=201)
def create_student(
    payload: StudentCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user, temporary = provision_student(
        db,
        actor_user_id=auth.user.id,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        roll_number=payload.roll_number,
        department=payload.department,
        programme=payload.programme,
        year=payload.year,
        division=payload.division,
        batch=payload.batch,
        admission_year=payload.admission_year,
        phone=payload.phone,
    )
    db.commit()
    db.refresh(user)
    return ProvisionedUserResponse(user=user_out(db, user), temporary_password=temporary)


@router.get("/teachers", response_model=list[UserOut])
def list_teachers(
    q: str | None = Query(default=None, max_length=120),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = (
        select(User)
        .join(TeacherProfile, TeacherProfile.user_id == User.id)
        .where(User.role == UserRole.TEACHER)
        .order_by(User.full_name)
    )
    if q:
        needle = f"%{q.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(User.full_name).like(needle),
                func.lower(User.email).like(needle),
                func.lower(TeacherProfile.employee_id).like(needle),
            )
        )
    return [user_out(db, user) for user in db.scalars(query).all()]


@router.post("/teachers", response_model=ProvisionedUserResponse, status_code=201)
def create_teacher(
    payload: TeacherCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user, temporary = provision_teacher(
        db,
        actor_user_id=auth.user.id,
        email=payload.email,
        full_name=payload.full_name,
        password=payload.password,
        employee_id=payload.employee_id,
        department=payload.department,
        designation=payload.designation,
        phone=payload.phone,
    )
    db.commit()
    db.refresh(user)
    return ProvisionedUserResponse(user=user_out(db, user), temporary_password=temporary)


# ---------------------------------------------------------------------------
# Classes and subjects
# ---------------------------------------------------------------------------
def _class_out(db: Session, item: SchoolClass, count: int = 0) -> ClassOut:
    return ClassOut(
        id=item.id,
        code=item.code,
        name=item.name,
        department=item.department,
        year=item.year,
        division=item.division,
        is_active=item.is_active,
        created_at=item.created_at,
        enrolled_count=count,
    )


@router.get("/classes", response_model=list[ClassOut])
def list_classes(auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    classes = db.scalars(select(SchoolClass).order_by(SchoolClass.name)).all()
    counts = dict(
        db.execute(
            select(ClassEnrollment.class_id, func.count(ClassEnrollment.id))
            .where(ClassEnrollment.status == EnrollmentStatus.ACTIVE)
            .group_by(ClassEnrollment.class_id)
        ).all()
    )
    return [_class_out(db, item, counts.get(item.id, 0)) for item in classes]


@router.post("/classes", response_model=ClassOut, status_code=201)
def create_class(
    payload: ClassCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    code = payload.code.strip()
    if db.scalar(select(SchoolClass.id).where(SchoolClass.code == code)):
        raise errors.conflict("A class with this code already exists.", "CLASS_CODE_EXISTS")
    item = SchoolClass(
        code=code,
        name=payload.name.strip(),
        department=payload.department.strip(),
        year=payload.year,
        division=payload.division.strip(),
    )
    db.add(item)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="CLASS_CREATED",
        entity_type="class",
        entity_id=item.id,
        details={"code": item.code},
    )
    db.commit()
    db.refresh(item)
    return _class_out(db, item)


@router.patch("/classes/{class_id}", response_model=ClassOut)
def update_class(
    class_id: uuid.UUID,
    payload: ClassUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(SchoolClass, class_id)
    if item is None:
        raise errors.not_found("Class not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(item, field, value)
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="CLASS_UPDATED",
        entity_type="class",
        entity_id=item.id,
        details={"fields": sorted(payload.model_dump(exclude_none=True).keys())},
    )
    db.commit()
    db.refresh(item)
    return _class_out(db, item)


@router.get("/subjects", response_model=list[SubjectOut])
def list_subjects(
    class_id: uuid.UUID | None = Query(default=None),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(Subject, SchoolClass).join(SchoolClass, SchoolClass.id == Subject.class_id)
    if class_id is not None:
        query = query.where(Subject.class_id == class_id)
    rows = db.execute(query.order_by(SchoolClass.name, Subject.name)).all()
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


@router.post("/subjects", response_model=SubjectOut, status_code=201)
def create_subject(
    payload: SubjectCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    school_class = db.get(SchoolClass, payload.class_id)
    if school_class is None:
        raise errors.not_found("Class not found.")
    code = payload.code.strip()
    if db.scalar(select(Subject.id).where(Subject.code == code)):
        raise errors.conflict("A subject with this code already exists.", "SUBJECT_CODE_EXISTS")
    subject = Subject(
        code=code,
        name=payload.name.strip(),
        class_id=school_class.id,
        credits=payload.credits,
    )
    db.add(subject)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="SUBJECT_CREATED",
        entity_type="subject",
        entity_id=subject.id,
        details={"code": subject.code, "class_id": str(school_class.id)},
    )
    db.commit()
    db.refresh(subject)
    return SubjectOut(
        id=subject.id,
        code=subject.code,
        name=subject.name,
        class_id=subject.class_id,
        class_code=school_class.code,
        class_name=school_class.name,
        credits=subject.credits,
        is_active=subject.is_active,
    )


@router.patch("/subjects/{subject_id}", response_model=SubjectOut)
def update_subject(
    subject_id: uuid.UUID,
    payload: SubjectUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise errors.not_found("Subject not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(subject, field, value)
    school_class = db.get(SchoolClass, subject.class_id)
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="SUBJECT_UPDATED",
        entity_type="subject",
        entity_id=subject.id,
        details={"fields": sorted(payload.model_dump(exclude_none=True).keys())},
    )
    db.commit()
    db.refresh(subject)
    return SubjectOut(
        id=subject.id,
        code=subject.code,
        name=subject.name,
        class_id=subject.class_id,
        class_code=school_class.code if school_class else None,
        class_name=school_class.name if school_class else None,
        credits=subject.credits,
        is_active=subject.is_active,
    )


# ---------------------------------------------------------------------------
# Classrooms
# ---------------------------------------------------------------------------
@router.get("/classrooms", response_model=list[ClassroomOut])
def list_classrooms(auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    rooms = db.scalars(select(Classroom).order_by(Classroom.name)).all()
    return [ClassroomOut.model_validate(room) for room in rooms]


@router.post("/classrooms", response_model=ClassroomOut, status_code=201)
def create_classroom(
    payload: ClassroomCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    code = payload.code.strip()
    if db.scalar(select(Classroom.id).where(Classroom.code == code)):
        raise errors.conflict("A classroom with this code already exists.", "ROOM_CODE_EXISTS")
    room = Classroom(
        code=code,
        name=payload.name.strip(),
        building=payload.building,
        floor=payload.floor,
        latitude=payload.latitude,
        longitude=payload.longitude,
        default_radius_m=payload.default_radius_m,
        max_accuracy_m=payload.max_accuracy_m,
    )
    db.add(room)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="CLASSROOM_CREATED",
        entity_type="classroom",
        entity_id=room.id,
        details={"code": room.code},
    )
    db.commit()
    db.refresh(room)
    return ClassroomOut.model_validate(room)


@router.patch("/classrooms/{room_id}", response_model=ClassroomOut)
def update_classroom(
    room_id: uuid.UUID,
    payload: ClassroomUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    room = db.get(Classroom, room_id)
    if room is None:
        raise errors.not_found("Classroom not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return ClassroomOut.model_validate(room)


# ---------------------------------------------------------------------------
# Enrolments and teaching assignments
# ---------------------------------------------------------------------------
def _enrollment_out(db: Session, item: ClassEnrollment) -> EnrollmentOut:
    school_class = db.get(SchoolClass, item.class_id)
    student = db.get(StudentProfile, item.student_id)
    user = db.get(User, student.user_id) if student else None
    return EnrollmentOut(
        id=item.id,
        class_id=item.class_id,
        class_name=school_class.name if school_class else "",
        student_id=item.student_id,
        student_name=user.full_name if user else "",
        roll_number=student.roll_number if student else "",
        status=item.status,
        enrolled_at=item.enrolled_at,
    )


@router.get("/enrollments", response_model=list[EnrollmentOut])
def list_enrollments(
    class_id: uuid.UUID | None = Query(default=None),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(ClassEnrollment).order_by(ClassEnrollment.enrolled_at.desc()).limit(1000)
    if class_id is not None:
        query = query.where(ClassEnrollment.class_id == class_id)
    return [_enrollment_out(db, item) for item in db.scalars(query).all()]


@router.post("/enrollments", response_model=EnrollmentBulkResponse, status_code=201)
def create_enrollments(
    payload: EnrollmentCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    school_class = db.get(SchoolClass, payload.class_id)
    if school_class is None:
        raise errors.not_found("Class not found.")
    students = db.scalars(
        select(StudentProfile).where(StudentProfile.id.in_(payload.student_ids))
    ).all()
    found_ids = {student.id for student in students}
    missing = set(payload.student_ids) - found_ids
    if missing:
        raise errors.bad_request(
            "One or more students were not found.", "STUDENT_NOT_FOUND", count=len(missing)
        )
    existing = set(
        db.scalars(
            select(ClassEnrollment.student_id).where(
                ClassEnrollment.class_id == school_class.id,
                ClassEnrollment.student_id.in_(found_ids),
            )
        ).all()
    )
    created: list[ClassEnrollment] = []
    for student in students:
        if student.id in existing:
            continue
        item = ClassEnrollment(
            class_id=school_class.id,
            student_id=student.id,
            status=EnrollmentStatus.ACTIVE,
        )
        db.add(item)
        created.append(item)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="ENROLLMENT_CREATED",
        entity_type="class",
        entity_id=school_class.id,
        details={"created": len(created), "skipped": len(existing)},
    )
    db.commit()
    return EnrollmentBulkResponse(
        created=len(created),
        skipped=len(existing),
        enrollments=[_enrollment_out(db, item) for item in created],
    )


@router.delete("/enrollments/{enrollment_id}")
def drop_enrollment(
    enrollment_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(ClassEnrollment, enrollment_id)
    if item is None:
        raise errors.not_found("Enrollment not found.")
    item.status = EnrollmentStatus.DROPPED
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="ENROLLMENT_DROPPED",
        entity_type="class_enrollment",
        entity_id=item.id,
        details={},
    )
    db.commit()
    return {"ok": True}


def _assignment_out(db: Session, item: TeacherAssignment) -> AssignmentOut:
    teacher = db.get(TeacherProfile, item.teacher_id)
    teacher_user = db.get(User, teacher.user_id) if teacher else None
    school_class = db.get(SchoolClass, item.class_id)
    subject = db.get(Subject, item.subject_id) if item.subject_id else None
    return AssignmentOut(
        id=item.id,
        teacher_id=item.teacher_id,
        teacher_name=teacher_user.full_name if teacher_user else "",
        class_id=item.class_id,
        class_name=school_class.name if school_class else "",
        subject_id=item.subject_id,
        subject_name=subject.name if subject else None,
        is_active=item.is_active,
        assigned_at=item.assigned_at,
    )


@router.get("/assignments", response_model=list[AssignmentOut])
def list_assignments(
    teacher_id: uuid.UUID | None = Query(default=None),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(TeacherAssignment).order_by(TeacherAssignment.assigned_at.desc()).limit(500)
    if teacher_id is not None:
        query = query.where(TeacherAssignment.teacher_id == teacher_id)
    return [_assignment_out(db, item) for item in db.scalars(query).all()]


@router.post("/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(
    payload: AssignmentCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    teacher = db.get(TeacherProfile, payload.teacher_id)
    if teacher is None:
        raise errors.not_found("Teacher not found.")
    school_class = db.get(SchoolClass, payload.class_id)
    if school_class is None:
        raise errors.not_found("Class not found.")
    if payload.subject_id is not None:
        subject = db.get(Subject, payload.subject_id)
        if subject is None or subject.class_id != school_class.id:
            raise errors.bad_request("The subject does not belong to this class.", "SUBJECT_CLASS_MISMATCH")
    duplicate = db.scalar(
        select(TeacherAssignment.id).where(
            TeacherAssignment.teacher_id == payload.teacher_id,
            TeacherAssignment.class_id == payload.class_id,
            TeacherAssignment.subject_id == payload.subject_id,
        )
    )
    if duplicate:
        raise errors.conflict("This teaching assignment already exists.", "ASSIGNMENT_EXISTS")
    item = TeacherAssignment(
        teacher_id=payload.teacher_id,
        class_id=payload.class_id,
        subject_id=payload.subject_id,
    )
    db.add(item)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="ASSIGNMENT_CREATED",
        entity_type="teacher_assignment",
        entity_id=item.id,
        details={
            "teacher_id": str(payload.teacher_id),
            "class_id": str(payload.class_id),
            "subject_id": str(payload.subject_id) if payload.subject_id else None,
        },
    )
    db.commit()
    return _assignment_out(db, item)


@router.delete("/assignments/{assignment_id}")
def deactivate_assignment(
    assignment_id: uuid.UUID,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(TeacherAssignment, assignment_id)
    if item is None:
        raise errors.not_found("Assignment not found.")
    item.is_active = False
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="ASSIGNMENT_DEACTIVATED",
        entity_type="teacher_assignment",
        entity_id=item.id,
        details={},
    )
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Attendance policies and geofences
# ---------------------------------------------------------------------------
@router.get("/policies", response_model=list[PolicyOut])
def list_policies(auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    policies = db.scalars(select(AttendancePolicy).order_by(AttendancePolicy.name)).all()
    return [PolicyOut.model_validate(item) for item in policies]


@router.post("/policies", response_model=PolicyOut, status_code=201)
def create_policy(
    payload: PolicyCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if db.scalar(select(AttendancePolicy.id).where(AttendancePolicy.name == payload.name.strip())):
        raise errors.conflict("A policy with this name already exists.", "POLICY_EXISTS")
    if payload.is_default:
        db.execute(
            update(AttendancePolicy)
            .where(AttendancePolicy.is_default.is_(True))
            .values(is_default=False)
        )
    item = AttendancePolicy(**payload.model_dump())
    item.name = item.name.strip()
    db.add(item)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="POLICY_CREATED",
        entity_type="attendance_policy",
        entity_id=item.id,
        details={"name": item.name},
    )
    db.commit()
    db.refresh(item)
    return PolicyOut.model_validate(item)


@router.patch("/policies/{policy_id}", response_model=PolicyOut)
def update_policy(
    policy_id: uuid.UUID,
    payload: PolicyUpdateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.get(AttendancePolicy, policy_id)
    if item is None:
        raise errors.not_found("Policy not found.")
    data = payload.model_dump(exclude_none=True)
    if data.get("is_default"):
        db.execute(
            update(AttendancePolicy)
            .where(AttendancePolicy.is_default.is_(True), AttendancePolicy.id != item.id)
            .values(is_default=False)
        )
    for field, value in data.items():
        setattr(item, field, value)
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="POLICY_UPDATED",
        entity_type="attendance_policy",
        entity_id=item.id,
        details={"fields": sorted(data.keys())},
    )
    db.commit()
    db.refresh(item)
    return PolicyOut.model_validate(item)


@router.get("/geofences", response_model=list[GeofenceOut])
def list_geofences(auth: AuthContext = Depends(require_admin), db: Session = Depends(get_db)):
    items = db.scalars(select(GeofencePolicy).order_by(GeofencePolicy.name)).all()
    return [GeofenceOut.model_validate(item) for item in items]


@router.post("/geofences", response_model=GeofenceOut, status_code=201)
def create_geofence(
    payload: GeofenceCreateRequest,
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if payload.classroom_id is not None and db.get(Classroom, payload.classroom_id) is None:
        raise errors.not_found("Classroom not found.")
    if db.scalar(select(GeofencePolicy.id).where(GeofencePolicy.name == payload.name.strip())):
        raise errors.conflict("A geofence with this name already exists.", "GEOFENCE_EXISTS")
    item = GeofencePolicy(**payload.model_dump())
    item.name = item.name.strip()
    db.add(item)
    db.flush()
    audit_service.audit(
        db,
        actor_user_id=auth.user.id,
        action="GEOFENCE_CREATED",
        entity_type="geofence_policy",
        entity_id=item.id,
        details={"name": item.name},
    )
    db.commit()
    db.refresh(item)
    return GeofenceOut.model_validate(item)


# ---------------------------------------------------------------------------
# Audit, security, imports
# ---------------------------------------------------------------------------
@router.get("/audit-logs", response_model=list[AuditEventOut])
def list_audit_logs(
    action: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=100000),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit).offset(offset)
    if action:
        query = query.where(AuditEvent.action == action)
    return [AuditEventOut.model_validate(item) for item in db.scalars(query).all()]


@router.get("/security-events", response_model=list[SecurityEventOut])
def list_security_events(
    severity: str | None = Query(default=None, max_length=20),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0, le=100000),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(limit).offset(offset)
    if severity:
        query = query.where(SecurityEvent.severity == severity)
    return [SecurityEventOut.model_validate(item) for item in db.scalars(query).all()]


@router.get("/imports/template", response_class=PlainTextResponse)
def import_template(
    kind: str = Query(default="students", pattern="^(students|teachers)$"),
    auth: AuthContext = Depends(require_admin),
):
    return PlainTextResponse(
        import_csv.template_csv(kind),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="attendx-{kind}-template.csv"'},
    )


async def _read_upload(file: UploadFile) -> bytes:
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise errors.bad_request("The CSV file must be smaller than 2 MB.", "FILE_TOO_LARGE")
    if not content:
        raise errors.bad_request("The uploaded file is empty.", "EMPTY_FILE")
    return content


@router.post("/imports/preview", response_model=ImportPreviewResponse)
async def preview_import(
    kind: str = Form(pattern="^(students|teachers)$"),
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = await _read_upload(file)
    return import_csv.preview(db, kind=kind, content=content)


@router.post("/imports/commit", response_model=ImportCommitResponse)
async def commit_import(
    kind: str = Form(pattern="^(students|teachers)$"),
    file: UploadFile = File(...),
    auth: AuthContext = Depends(require_admin),
    db: Session = Depends(get_db),
):
    content = await _read_upload(file)
    return import_csv.commit(
        db, actor_user_id=auth.user.id, kind=kind, content=content, filename=file.filename
    )
