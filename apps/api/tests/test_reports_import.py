"""Reports and CSV provisioning tests."""
from __future__ import annotations

from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    TEACHER_EMAIL,
    TEACHER_PASSWORD,
    login,
    open_attendance_session,
)


def test_attendance_report_after_verified_flow(client, seeded):
    teacher_csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    opened = open_attendance_session(client, teacher_csrf, seeded)
    session_id = opened["session_id"]

    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    checkin = client.post(
        "/api/v1/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    ).json()
    attempt_id = checkin["attempt"]["id"]
    client.post(f"/api/v1/attendance/attempts/{attempt_id}/pin", json={"pin": opened["pin"]})
    client.post(
        f"/api/v1/attendance/attempts/{attempt_id}/location",
        json={"latitude": 18.5205, "longitude": 73.8568, "accuracy_m": 20},
    )
    assert client.post(f"/api/v1/attendance/attempts/{attempt_id}/finalize").status_code == 200

    login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    report = client.get(
        "/api/v1/reports/attendance", params={"class_id": seeded["class_id"]}
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["totals"]["students"] == 2
    assert body["totals"]["sessions"] == 1
    by_roll = {row["roll_number"]: row for row in body["rows"]}
    assert by_roll["ROLL-TEST-001"]["sessions_present"] == 1
    assert by_roll["ROLL-TEST-001"]["attendance_percentage"] == 100.0
    assert by_roll["ROLL-TEST-002"]["sessions_present"] == 0
    assert by_roll["ROLL-TEST-002"]["attendance_percentage"] == 0.0

    export = client.get("/api/v1/reports/export", params={"class_id": seeded["class_id"]})
    assert export.status_code == 200
    assert "text/csv" in export.headers["content-type"]
    assert "ROLL-TEST-001" in export.text


def test_teacher_can_only_report_on_assigned_class(client, seeded, db):
    from app.models import SchoolClass

    other = SchoolClass(code="TEST-OTHER", name="Other Class", department="Civil", year=1, division="B")
    db.add(other)
    db.commit()
    login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    response = client.get("/api/v1/reports/attendance", params={"class_id": str(other.id)})
    assert response.status_code == 403


def test_csv_preview_commit_and_login(client, seeded):
    csrf = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    csv_content = (
        "email,full_name,roll_number,department,programme,year,division,batch,admission_year,phone\n"
        "imported@attendx.dev,Imported Student,ROLL-IMP-001,Computer Engineering,B.E.,2,B,,2024,\n"
        "bad-email,Second Import,ROLL-IMP-002,Computer Engineering,B.E.,2,B,,2024,\n"
    ).encode()
    preview = client.post(
        "/api/v1/admin/imports/preview",
        data={"kind": "students"},
        files={"file": ("students.csv", csv_content, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 1
    assert body["invalid_rows"] == 1

    commit = client.post(
        "/api/v1/admin/imports/commit",
        data={"kind": "students"},
        files={"file": ("students.csv", csv_content, "text/csv")},
        headers={"X-CSRF-Token": csrf},
    )
    assert commit.status_code == 200, commit.text
    result = commit.json()
    assert result["success_rows"] == 1
    assert result["error_rows"] == 1
    created = result["created_users"][0]
    assert created["temporary_password"]

    login(client, "imported@attendx.dev", created["temporary_password"])
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["must_change_password"] is True
    assert me.json()["user"]["student"]["roll_number"] == "ROLL-IMP-001"


def test_import_template_available(client, seeded):
    login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    response = client.get("/api/v1/admin/imports/template", params={"kind": "students"})
    assert response.status_code == 200
    assert "roll_number" in response.text
    assert "email" in response.text
