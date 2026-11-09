"""Live integration check against a running AttendX API.

Requires a seeded development database (app.scripts.seed_dev) and the API listening
on 127.0.0.1:8000. This complements the isolated pytest suite by exercising a real
HTTP server, cookies, CSRF and persistence.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
TEACHER = ("teacher@attendx.dev", "SeedTeacher!2345")
STUDENT = ("student1@attendx.dev", "SeedStudent!2345")
ADMIN = ("admin@attendx.dev", "SeedAdmin!2345")


def login(client: httpx.Client, email: str, password: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": password})
    response.raise_for_status()
    csrf = response.json()["csrf_token"]
    client.headers["X-CSRF-Token"] = csrf
    return csrf


def main() -> int:
    results: dict = {}
    with httpx.Client(base_url=BASE, timeout=30.0) as teacher:
        login(teacher, *TEACHER)
        classes = teacher.get("/teacher/classes").json()
        assignments = teacher.get("/teacher/subjects").json()
        classrooms = teacher.get("/classrooms").json()
        requires_face = False
        class_id = classes[0]["id"]
        assignment = next(item for item in assignments if item["class_id"] == class_id)
        starts = datetime.now(timezone.utc).isoformat()
        created = teacher.post(
            "/teacher/sessions",
            json={
                "class_id": class_id,
                "subject_id": assignment["subject_id"],
                "classroom_id": classrooms[0]["id"],
                "starts_at": starts,
                "window_seconds": 180,
                "qr_refresh_seconds": 30,
            },
        )
        created.raise_for_status()
        session = created.json()
        results["session_created"] = session["id"]
        results["policy_snapshot"] = {
            "pin": session["require_pin"],
            "geofence": session["require_geofence"],
            "face": session["require_face"],
            "liveness": session["require_liveness"],
        }
        assert session["require_pin"] is True
        assert session["require_geofence"] is True
        requires_face = session["require_face"]

        opened = teacher.post(f"/teacher/sessions/{session['id']}/open")
        opened.raise_for_status()
        open_payload = opened.json()
        assert open_payload["pin"] and open_payload["qr"]["token"]
        results["pin_issued"] = True

    with httpx.Client(base_url=BASE, timeout=30.0) as student:
        login(student, *STUDENT)
        validated = student.post("/attendance/qr/validate", json={"token": open_payload["qr"]["token"]})
        validated.raise_for_status()
        results["qr_validated"] = validated.json()["session_id"] == session["id"]
        assert validated.json()["can_check_in"] is True

        checkin = student.post(
            "/attendance/check-ins", json={"qr_token": open_payload["qr"]["token"]}
        )
        checkin.raise_for_status()
        attempt = checkin.json()["attempt"]
        results["attempt"] = attempt["id"]
        assert checkin.json()["next_step"] == "pin"

        pin_response = student.post(
            f"/attendance/attempts/{attempt['id']}/pin", json={"pin": open_payload["pin"]}
        )
        pin_response.raise_for_status()
        results["pin_status"] = pin_response.json()["attempt"]["pin_status"]
        assert results["pin_status"] == "PASSED"

        location = student.post(
            f"/attendance/attempts/{attempt['id']}/location",
            json={
                "latitude": 18.5205,
                "longitude": 73.8568,
                "accuracy_m": 20,
                "client_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        location.raise_for_status()
        results["gps_status"] = location.json()["gps_status"]
        results["distance_m"] = location.json()["distance_m"]
        assert results["gps_status"] == "INSIDE_GEOFENCE"

        if requires_face:
            # With no provider configured this must be an honest UNAVAILABLE state.
            face = student.post(f"/attendance/attempts/{attempt['id']}/face")
            face.raise_for_status()
            results["face_status"] = face.json()["status"]
            assert face.json()["status"] == "UNAVAILABLE"

        finalize = student.post(f"/attendance/attempts/{attempt['id']}/finalize")
        finalize.raise_for_status()
        final = finalize.json()
        results["decision"] = final["decision"]
        results["status"] = final["status"]
        results["classification"] = final["classification"]
        results["reference"] = final["reference"]
        expected = "REVIEW_REQUIRED" if requires_face else "ACCEPTED"
        assert final["decision"] == expected, final

        duplicate = student.post(
            "/attendance/check-ins", json={"qr_token": open_payload["qr"]["token"]}
        )
        results["duplicate_status_code"] = duplicate.status_code
        assert duplicate.status_code == 409

        dashboard = student.get("/student/dashboard")
        dashboard.raise_for_status()
        results["student_dashboard"] = {
            "total": dashboard.json()["total_sessions"],
            "attended": dashboard.json()["attended_sessions"],
        }

    with httpx.Client(base_url=BASE, timeout=30.0) as teacher:
        login(teacher, *TEACHER)
        live = teacher.get(f"/teacher/sessions/{session['id']}/live")
        live.raise_for_status()
        counts = live.json()["session"]
        results["live_counts"] = {
            "eligible": counts["eligible_students"],
            "accepted": counts["accepted"],
            "review": counts["review_required"],
        }
        assert counts["eligible_students"] == 8
        assert counts["accepted"] >= 1

    with httpx.Client(base_url=BASE, timeout=30.0) as admin:
        login(admin, *ADMIN)
        report = admin.get("/reports/attendance", params={"class_id": class_id})
        report.raise_for_status()
        body = report.json()
        results["report"] = {
            "students": body["totals"]["students"],
            "sessions": body["totals"]["sessions"],
            "present": body["totals"]["present"],
        }
        export = admin.get("/reports/export", params={"class_id": class_id})
        export.raise_for_status()
        results["export_bytes"] = len(export.content)
        assert "text/csv" in export.headers["content-type"]
        health = admin.get("/health/ready")
        health.raise_for_status()
        results["health"] = health.json()

    print(json.dumps(results, indent=2, default=str))
    print("LIVE_FLOW_PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"LIVE_FLOW_FAIL: {exc}", file=sys.stderr)
        raise
