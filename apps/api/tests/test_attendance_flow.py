"""PIN verification, attempt limits, duplicate prevention and finalization."""
from __future__ import annotations

from datetime import datetime, timezone

from tests.conftest import (
    STUDENT2_EMAIL,
    STUDENT2_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    TEACHER_EMAIL,
    TEACHER_PASSWORD,
    login,
    open_attendance_session,
)


def test_correct_pin_advances_attempt(client, seeded):
    teacher_csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    opened = open_attendance_session(client, teacher_csrf, seeded)

    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    checkin = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    assert checkin.status_code == 201, checkin.text
    attempt_id = checkin.json()["attempt"]["id"]
    assert checkin.json()["next_step"] == "pin"

    result = client.post(
        f"/api/v1/attendance/attempts/{attempt_id}/pin", json={"pin": opened["pin"]}
    )
    assert result.status_code == 200, result.text
    assert result.json()["attempt"]["pin_status"] == "PASSED"
    assert result.json()["next_step"] == "gps"


def test_pin_attempt_limit_creates_rejected_record(client, seeded):
    teacher_csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    opened = open_attendance_session(client, teacher_csrf, seeded)

    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    checkin = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    attempt_id = checkin.json()["attempt"]["id"]

    wrong = "000000" if opened["pin"] != "000000" else "111111"
    for index in range(4):
        response = client.post(
            f"/api/v1/attendance/attempts/{attempt_id}/pin", json={"pin": wrong}
        )
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "PIN_INVALID"
        assert f"{4 - index} attempt(s) remaining" in response.text

    fifth = client.post(f"/api/v1/attendance/attempts/{attempt_id}/pin", json={"pin": wrong})
    assert fifth.status_code == 400

    history = client.get("/api/v1/student/attendance")
    assert history.status_code == 200
    assert any(item["status"] == "rejected" for item in history.json())

    duplicate = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ALREADY_RECORDED"


def test_full_verified_flow_and_duplicate_prevention(client, seeded):
    teacher_csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    opened = open_attendance_session(client, teacher_csrf, seeded)
    session_id = opened["session_id"]

    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    checkin = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    assert checkin.status_code == 201, checkin.text
    attempt_id = checkin.json()["attempt"]["id"]

    pin = client.post(
        f"/api/v1/attendance/attempts/{attempt_id}/pin", json={"pin": opened["pin"]}
    )
    assert pin.status_code == 200

    location = client.post(
        f"/api/v1/attendance/attempts/{attempt_id}/location",
        json={
            "latitude": 18.5205,
            "longitude": 73.8568,
            "accuracy_m": 20,
            "client_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert location.status_code == 200, location.text
    assert location.json()["gps_status"] == "INSIDE_GEOFENCE"
    assert location.json()["distance_m"] is not None

    final = client.post(f"/api/v1/attendance/attempts/{attempt_id}/finalize")
    assert final.status_code == 200, final.text
    payload = final.json()
    assert payload["decision"] == "ACCEPTED"
    assert payload["status"] == "present"
    assert payload["classification"] == "FULL"
    assert payload["reference"].startswith("AX-")

    duplicate = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ALREADY_RECORDED"

    history = client.get("/api/v1/student/attendance")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["reference"] == payload["reference"]

    dashboard = client.get("/api/v1/student/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["attended_sessions"] == 1
    assert dashboard.json()["attendance_percentage"] == 100.0

    # Teacher live view must reflect the database, not local state.
    login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    live = client.get(f"/api/v1/teacher/sessions/{session_id}/live")
    assert live.status_code == 200
    assert live.json()["session"]["accepted"] == 1
    assert live.json()["session"]["pending"] == 0
    assert live.json()["session"]["eligible_students"] == 2


def test_finalize_requires_completed_steps(client, seeded):
    teacher_csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    opened = open_attendance_session(client, teacher_csrf, seeded)

    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    checkin = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    attempt_id = checkin.json()["attempt"]["id"]
    early = client.post(f"/api/v1/attendance/attempts/{attempt_id}/finalize")
    assert early.status_code == 400
    assert early.json()["error"]["code"] == "VERIFICATION_PENDING"


def test_non_enrolled_student_cannot_check_in(client, seeded):
    teacher_csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    opened = open_attendance_session(client, teacher_csrf, seeded)

    # Student two is enrolled in the fixture; remove the enrolment through the API
    # requires admin. Instead verify the negative path with a fresh unenrolled student.
    from app.models import ClassEnrollment, StudentProfile
    from tests.conftest import login as do_login

    admin_csrf = do_login(client, "admin@attendx.dev", "AdminPass!2345")
    assert admin_csrf
    from app.services.users import provision_student

    # Use the API to create a student in another division but do not enrol them.
    created = client.post(
        "/api/v1/admin/students",
        json={
            "email": "unenrolled@attendx.dev",
            "full_name": "Unenrolled Student",
            "password": "Unenrolled!2345",
            "roll_number": "ROLL-UNENROLLED",
            "department": "Computer Engineering",
            "year": 3,
            "division": "B",
        },
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert created.status_code == 201, created.text

    login(client, "unenrolled@attendx.dev", "Unenrolled!2345")
    response = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    assert response.status_code == 403
