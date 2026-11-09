"""Shared pytest fixtures. Tests run against an isolated in-memory SQLite database."""
from __future__ import annotations

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///./attendx_test_placeholder.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("QR_SIGNING_KEY", "test-qr-signing-key-not-for-production")
os.environ.setdefault("WEB_ORIGIN", "http://testserver")
os.environ.setdefault("COOKIE_SECURE", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.db import get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models import (
    AttendancePolicy,
    Base,
    ClassEnrollment,
    Classroom,
    SchoolClass,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
)
from app.services.auth import bootstrap_admin
from app.services.users import provision_student, provision_teacher

POSTGRES_TEST_URL = os.environ.get("TEST_DATABASE_URL", "").strip()
if POSTGRES_TEST_URL:
    # The same suite can run against real PostgreSQL in CI/staging.
    engine = create_engine(POSTGRES_TEST_URL, future=True, pool_pre_ping=True)
else:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
Base.metadata.create_all(engine)


def _override_get_db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = _override_get_db

ADMIN_EMAIL = "admin@attendx.dev"
ADMIN_PASSWORD = "AdminPass!2345"
TEACHER_EMAIL = "teacher@attendx.dev"
TEACHER_PASSWORD = "TeacherPass!2345"
STUDENT_EMAIL = "student1@attendx.dev"
STUDENT_PASSWORD = "StudentPass!2345"
STUDENT2_EMAIL = "student2@attendx.dev"
STUDENT2_PASSWORD = "StudentPass!2345"


@pytest.fixture(autouse=True)
def _reset_limiter():
    limiter.clear()
    yield
    limiter.clear()


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client():
    return TestClient(app)


def login(client: TestClient, email: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    csrf = response.json()["csrf_token"]
    # Keep the double-submit header in sync with the active session for all
    # subsequent mutating test requests.
    client.headers["X-CSRF-Token"] = csrf
    return csrf


def open_attendance_session(client: TestClient, csrf: str, seeded: dict) -> dict:
    """Create and open a session; returns the open response payload plus session id."""
    from datetime import datetime, timezone

    created = client.post(
        "/api/v1/teacher/sessions",
        json={
            "class_id": seeded["class_id"],
            "subject_id": seeded["subject_id"],
            "classroom_id": seeded["classroom_id"],
            "starts_at": datetime.now(timezone.utc).isoformat(),
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    opened = client.post(
        f"/api/v1/teacher/sessions/{session_id}/open",
        headers={"X-CSRF-Token": csrf},
    )
    assert opened.status_code == 200, opened.text
    payload = opened.json()
    payload["session_id"] = session_id
    return payload


@pytest.fixture()
def seeded(db):
    """A minimal, explicitly test-only academic fixture. No production data."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    admin = bootstrap_admin(
        db, email=ADMIN_EMAIL, password=ADMIN_PASSWORD, full_name="Test Administrator"
    )
    teacher, _ = provision_teacher(
        db,
        actor_user_id=admin.id,
        email=TEACHER_EMAIL,
        full_name="Test Teacher",
        password=TEACHER_PASSWORD,
        employee_id="EMP-TEST-001",
        department="Computer Engineering",
        designation="Assistant Professor",
    )
    student, _ = provision_student(
        db,
        actor_user_id=admin.id,
        email=STUDENT_EMAIL,
        full_name="Test Student One",
        password=STUDENT_PASSWORD,
        roll_number="ROLL-TEST-001",
        department="Computer Engineering",
        programme="B.E.",
        year=3,
        division="A",
        batch=None,
        admission_year=2023,
    )
    student2, _ = provision_student(
        db,
        actor_user_id=admin.id,
        email=STUDENT2_EMAIL,
        full_name="Test Student Two",
        password=STUDENT2_PASSWORD,
        roll_number="ROLL-TEST-002",
        department="Computer Engineering",
        programme="B.E.",
        year=3,
        division="A",
        batch=None,
        admission_year=2023,
    )
    school_class = SchoolClass(
        code="TEST-CE-3A",
        name="TE Computer A",
        department="Computer Engineering",
        year=3,
        division="A",
    )
    db.add(school_class)
    db.flush()
    subject = Subject(code="TEST-DBMS", name="Database Management Systems", class_id=school_class.id)
    db.add(subject)
    classroom = Classroom(
        code="TEST-ROOM-101",
        name="Test Classroom 101",
        building="Test Block",
        latitude=18.5204,
        longitude=73.8567,
        default_radius_m=80.0,
        max_accuracy_m=100.0,
    )
    db.add(classroom)
    policy = AttendancePolicy(name="Test default policy", is_default=True)
    db.add(policy)
    db.flush()

    teacher_profile = db.scalars(
        select(TeacherProfile).where(TeacherProfile.user_id == teacher.id)
    ).one()
    student_profile = db.scalars(
        select(StudentProfile).where(StudentProfile.user_id == student.id)
    ).one()
    student2_profile = db.scalars(
        select(StudentProfile).where(StudentProfile.user_id == student2.id)
    ).one()

    for profile in (student_profile, student2_profile):
        db.add(ClassEnrollment(class_id=school_class.id, student_id=profile.id))
    db.add(
        TeacherAssignment(
            teacher_id=teacher_profile.id, class_id=school_class.id, subject_id=subject.id
        )
    )
    db.commit()
    db.refresh(student_profile)
    db.refresh(student2_profile)
    return {
        "admin_id": str(admin.id),
        "teacher_id": str(teacher_profile.id),
        "teacher_user_id": str(teacher.id),
        "class_id": str(school_class.id),
        "subject_id": str(subject.id),
        "classroom_id": str(classroom.id),
        "policy_id": str(policy.id),
        "student_id": str(student_profile.id),
        "student2_id": str(student2_profile.id),
        "student_email": STUDENT_EMAIL,
        "student2_email": STUDENT2_EMAIL,
        "student_password": STUDENT_PASSWORD,
        "student2_password": STUDENT2_PASSWORD,
    }


@pytest.fixture()
def settings():
    return get_settings()
