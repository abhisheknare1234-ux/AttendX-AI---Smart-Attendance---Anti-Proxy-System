"""Authentication, session and authorization tests."""
from __future__ import annotations

from sqlalchemy import select

from app.models import TeacherProfile
from app.services.users import provision_teacher
from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    STUDENT2_PASSWORD,
    TEACHER_EMAIL,
    TEACHER_PASSWORD,
    login,
)


def test_login_me_and_logout(client, seeded):
    csrf = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["role"] == "admin"
    assert me.json()["csrf_token"] == csrf

    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 401


def test_wrong_password_is_generic_and_locks_account(client, seeded):
    for _ in range(5):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": STUDENT_EMAIL, "password": "WrongPassword!1"},
        )
        assert response.status_code == 401
        assert "Invalid email or password" in response.text

    locked = client.post(
        "/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD}
    )
    assert locked.status_code == 401


def test_csrf_required_for_mutations(client, seeded):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    client.headers.pop("X-CSRF-Token", None)
    response = client.patch(
        f"/api/v1/admin/users/{seeded['admin_id']}", json={"full_name": "Renamed Admin"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_FAILED"


def test_student_cannot_access_admin(client, seeded):
    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    response = client.get("/api/v1/admin/users")
    assert response.status_code == 403


def test_teacher_cannot_access_another_teachers_session(client, seeded, db):
    import uuid as uuid_module

    from app.core.timeutil import utcnow
    from app.models import AttendanceSession, SessionStatus

    other_user, _ = provision_teacher(
        db,
        actor_user_id=uuid_module.UUID(seeded["teacher_user_id"]),
        email="other.teacher@attendx.dev",
        full_name="Other Teacher",
        password="OtherTeacher!2345",
        employee_id="EMP-TEST-002",
        department="Computer Engineering",
        designation="Assistant Professor",
    )
    other_profile = db.scalars(
        select(TeacherProfile).where(TeacherProfile.user_id == other_user.id)
    ).one()
    session = AttendanceSession(
        class_id=uuid_module.UUID(seeded["class_id"]),
        subject_id=uuid_module.UUID(seeded["subject_id"]),
        classroom_id=uuid_module.UUID(seeded["classroom_id"]),
        teacher_id=other_profile.id,
        status=SessionStatus.SCHEDULED,
        starts_at=utcnow(),
        ends_at=utcnow(),
        created_by_id=uuid_module.UUID(seeded["admin_id"]),
    )
    db.add(session)
    db.commit()

    login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    response = client.get(f"/api/v1/teacher/sessions/{session.id}")
    assert response.status_code == 403


def test_password_change_flow(client, seeded):
    csrf = login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    response = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": STUDENT_PASSWORD, "new_password": "NewStudentPass!2345"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    login(client, STUDENT_EMAIL, "NewStudentPass!2345")


def test_second_student_can_login(client, seeded):
    login(client, "student2@attendx.dev", STUDENT2_PASSWORD)
    assert client.get("/api/v1/auth/me").status_code == 200
