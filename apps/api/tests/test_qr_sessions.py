"""QR signing, rotation, expiry and session lifecycle tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import sign_qr_payload, verify_qr_signature
from app.models import QrToken
from tests.conftest import ADMIN_PASSWORD, TEACHER_EMAIL, TEACHER_PASSWORD, login


def _create_and_open(client, csrf):
    starts = datetime.now(timezone.utc)
    created = client.post(
        "/api/v1/teacher/sessions",
        json={
            "class_id": None,  # replaced by caller
        },
        headers={"X-CSRF-Token": csrf},
    )
    return created


def test_qr_signature_tamper_rejected():
    token = sign_qr_payload(
        {"sid": "00000000-0000-0000-0000-000000000000", "nonce": "abc", "iat": 1, "exp": 2},
        "test-key",
    )
    assert verify_qr_signature(token, "test-key") is not None
    assert verify_qr_signature(token, "wrong-key") is None
    assert verify_qr_signature(token[:-1] + ("A" if token[-1] != "A" else "B"), "test-key") is None
    assert verify_qr_signature("not-a-token", "test-key") is None


def test_open_session_returns_pin_and_qr(client, seeded, settings):
    csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
    starts = datetime.now(timezone.utc).isoformat()
    created = client.post(
        "/api/v1/teacher/sessions",
        json={
            "class_id": seeded["class_id"],
            "subject_id": seeded["subject_id"],
            "classroom_id": seeded["classroom_id"],
            "starts_at": starts,
        },
        headers={"X-CSRF-Token": csrf},
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["id"]
    assert created.json()["status"] == "scheduled"

    opened = client.post(
        f"/api/v1/teacher/sessions/{session_id}/open", headers={"X-CSRF-Token": csrf}
    )
    assert opened.status_code == 200, opened.text
    body = opened.json()
    assert body["pin"] and body["pin"].isdigit()
    assert body["qr"]["token"].count(".") == 2
    assert body["session"]["status"] == "open"
    assert body["session"]["pin_available"] is True

    live = client.get(f"/api/v1/teacher/sessions/{session_id}/live")
    assert live.status_code == 200
    assert live.json()["qr"]["token"] == body["qr"]["token"]

    rotated = client.post(
        f"/api/v1/teacher/sessions/{session_id}/qr", headers={"X-CSRF-Token": csrf}
    )
    assert rotated.status_code == 200
    assert rotated.json()["token"] != body["qr"]["token"]


def test_old_token_stays_valid_until_its_expiry_after_rotation(client, seeded):
    csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
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
    session_id = created.json()["id"]
    opened = client.post(
        f"/api/v1/teacher/sessions/{session_id}/open", headers={"X-CSRF-Token": csrf}
    ).json()
    old_token = opened["qr"]["token"]
    client.post(f"/api/v1/teacher/sessions/{session_id}/qr", headers={"X-CSRF-Token": csrf})

    login(client, seeded["student_email"], seeded["student_password"])
    validated = client.post("/api/v1/attendance/qr/validate", json={"token": old_token})
    assert validated.status_code == 200, validated.text
    assert validated.json()["session_id"] == session_id


def test_closed_session_invalidates_qr(client, seeded, db):
    csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
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
    session_id = created.json()["id"]
    opened = client.post(
        f"/api/v1/teacher/sessions/{session_id}/open", headers={"X-CSRF-Token": csrf}
    ).json()
    token = opened["qr"]["token"]

    closed = client.post(
        f"/api/v1/teacher/sessions/{session_id}/close", headers={"X-CSRF-Token": csrf}
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    login(client, seeded["student_email"], seeded["student_password"])
    validated = client.post("/api/v1/attendance/qr/validate", json={"token": token})
    assert validated.status_code in {400, 409}
    assert validated.json()["error"]["code"] in {"QR_REVOKED", "SESSION_NOT_OPEN"}


def test_expired_token_rejected(client, seeded, db):
    import uuid as uuid_module

    csrf = login(client, TEACHER_EMAIL, TEACHER_PASSWORD)
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
    session_id = created.json()["id"]
    opened = client.post(
        f"/api/v1/teacher/sessions/{session_id}/open", headers={"X-CSRF-Token": csrf}
    ).json()
    token = opened["qr"]["token"]
    db.rollback()
    row = db.scalar(select(QrToken).where(QrToken.session_id == uuid_module.UUID(session_id)))
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()

    login(client, seeded["student_email"], seeded["student_password"])
    validated = client.post("/api/v1/attendance/qr/validate", json={"token": token})
    assert validated.status_code == 400
    assert validated.json()["error"]["code"] == "QR_EXPIRED"


def test_invalid_token_rejected(client, seeded):
    login(client, seeded["student_email"], seeded["student_password"])
    response = client.post("/api/v1/attendance/qr/validate", json={"token": "v1.bogus.signature"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "QR_INVALID"
