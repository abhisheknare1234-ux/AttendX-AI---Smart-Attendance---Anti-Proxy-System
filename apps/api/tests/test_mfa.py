"""TOTP MFA enrollment and challenge-login tests."""
from __future__ import annotations

from app.core.totp import verify_totp
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD, login

# RFC 6238 test seed; the RFC's 8-digit value at t=59 is 94287082, so the
# 6-digit value is 287082.
RFC_SECRET = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"


def test_totp_known_vector():
    from datetime import datetime, timezone

    assert verify_totp(RFC_SECRET, "287082", at=datetime.fromtimestamp(59, timezone.utc))
    assert not verify_totp(RFC_SECRET, "000000", at=datetime.fromtimestamp(59, timezone.utc))


def test_enable_login_with_mfa_and_disable(client, seeded):
    csrf = login(client, ADMIN_EMAIL, ADMIN_PASSWORD)
    setup = client.post("/api/v1/auth/mfa/setup", headers={"X-CSRF-Token": csrf})
    assert setup.status_code == 200, setup.text
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")

    from app.core.totp import totp

    enable = client.post(
        "/api/v1/auth/mfa/enable",
        json={"code": totp(secret)},
        headers={"X-CSRF-Token": csrf},
    )
    assert enable.status_code == 200, enable.text
    assert enable.json()["enabled"] is True

    # Log out, then a correct password must return a challenge instead of a session.
    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    challenge_response = client.post(
        "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert challenge_response.status_code == 200, challenge_response.text
    body = challenge_response.json()
    assert body["mfa_required"] is True
    assert "challenge_token" in body
    token = body["challenge_token"]

    wrong = client.post(
        "/api/v1/auth/mfa/verify", json={"challenge_token": token, "code": "000000"}
    )
    assert wrong.status_code == 400
    assert wrong.json()["error"]["code"] == "MFA_CODE_INVALID"

    verified = client.post(
        "/api/v1/auth/mfa/verify",
        json={"challenge_token": token, "code": totp(secret)},
    )
    assert verified.status_code == 200, verified.text
    assert verified.json()["user"]["role"] == "admin"
    csrf = verified.json()["csrf_token"]
    assert client.get("/api/v1/auth/me").status_code == 200

    # Disable MFA with the password and a current code.
    disabled = client.post(
        "/api/v1/auth/mfa/disable",
        json={"password": ADMIN_PASSWORD, "code": totp(secret)},
        headers={"X-CSRF-Token": csrf},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["enabled"] is False

    client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    normal = client.post(
        "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert normal.status_code == 200
    assert "mfa_required" not in normal.json()
