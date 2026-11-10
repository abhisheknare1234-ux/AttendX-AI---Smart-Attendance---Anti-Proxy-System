"""Administrator-issued password reset token tests."""
from __future__ import annotations

from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    STUDENT_EMAIL,
    STUDENT_PASSWORD,
    login,
)


def test_password_reset_token_flow(client, seeded):
    admin_csrf = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    issued = client.post(
        f"/api/v1/admin/users/{seeded['student_user_id']}/password-reset",
        headers={"X-CSRF-Token": admin_csrf},
    )
    assert issued.status_code == 200, issued.text
    body = issued.json()
    assert body["token"]
    assert body["reset_url"].endswith(body["token"])

    # The student is not required to be signed in to redeem the token.
    reset = client.post(
        "/api/v1/auth/reset-password",
        json={"token": body["token"], "new_password": "ResetStudent!2345"},
    )
    assert reset.status_code == 200, reset.text

    reused = client.post(
        "/api/v1/auth/reset-password",
        json={"token": body["token"], "new_password": "AnotherReset!2345"},
    )
    assert reused.status_code == 400
    assert reused.json()["error"]["code"] == "PASSWORD_RESET_INVALID"

    old_login = client.post(
        "/api/v1/auth/login", json={"email": STUDENT_EMAIL, "password": STUDENT_PASSWORD}
    )
    assert old_login.status_code == 401
    login(client, STUDENT_EMAIL, "ResetStudent!2345")


def test_invalid_reset_token_rejected(client, seeded):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "x" * 48, "new_password": "SomePassword!2345"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PASSWORD_RESET_INVALID"
