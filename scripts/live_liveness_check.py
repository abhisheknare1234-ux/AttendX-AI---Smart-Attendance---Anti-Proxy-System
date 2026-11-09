"""Live face + liveness attendance check.

Requires the API to be running with:
    FACE_PROVIDER=local_opencv
    LIVENESS_PROVIDER=local_minifas
    FACE_MODEL_DIR=<models dir>
    LIVENESS_MODEL_DIR=<models dir>
    FACE_TEMPLATE_KEY=<key>

and a development database seeded with app.scripts.seed_dev. The spoof input is a
synthetic print-like (grayscale) transform used only as a sanity check, not a
validated presentation-attack evaluation.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000/api/v1"
TEACHER = ("teacher@attendx.dev", "SeedTeacher!2345")
STUDENT = ("student1@attendx.dev", "SeedStudent!2345")
REFERENCE = ROOT / ".cache" / "facedata" / "astronaut-v024.bin"
FACE_PROBE = ROOT / ".cache" / "facedata" / "astronaut-flipped.jpg"
LIVE_PROBE = ROOT / ".cache" / "facedata" / "astronaut-v024.bin"
SPOOF_PROBE = ROOT / ".cache" / "facedata" / "astronaut-gray.jpg"


def login(client: httpx.Client, credentials: tuple[str, str]) -> None:
    response = client.post("/auth/login", json={"email": credentials[0], "password": credentials[1]})
    response.raise_for_status()
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]


def create_and_open(client: httpx.Client) -> dict:
    classes = client.get("/teacher/classes").json()
    assignments = client.get("/teacher/subjects").json()
    classrooms = client.get("/classrooms").json()
    class_id = classes[0]["id"]
    assignment = next(item for item in assignments if item["class_id"] == class_id)
    created = client.post(
        "/teacher/sessions",
        json={
            "class_id": class_id,
            "subject_id": assignment["subject_id"],
            "classroom_id": classrooms[0]["id"],
            "starts_at": datetime.now(timezone.utc).isoformat(),
            "window_seconds": 180,
            "require_pin": True,
            "require_geofence": True,
            "require_face": True,
            "require_liveness": True,
        },
    )
    created.raise_for_status()
    session = created.json()
    opened = client.post(f"/teacher/sessions/{session['id']}/open")
    opened.raise_for_status()
    payload = opened.json()
    payload["session_id"] = session["id"]
    return payload


def attempt(student: httpx.Client, opened: dict, liveness_image: Path) -> dict:
    checkin = student.post("/attendance/check-ins", json={"qr_token": opened["qr"]["token"]})
    checkin.raise_for_status()
    attempt_id = checkin.json()["attempt"]["id"]
    student.post(f"/attendance/attempts/{attempt_id}/pin", json={"pin": opened["pin"]}).raise_for_status()
    student.post(
        f"/attendance/attempts/{attempt_id}/location",
        json={
            "latitude": 18.5205,
            "longitude": 73.8568,
            "accuracy_m": 20,
            "client_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    ).raise_for_status()
    face = student.post(
        f"/attendance/attempts/{attempt_id}/face",
        files={"image": (FACE_PROBE.name, FACE_PROBE.read_bytes(), "image/jpeg")},
    )
    face.raise_for_status()
    liveness = student.post(
        f"/attendance/attempts/{attempt_id}/liveness",
        files={"image": (liveness_image.name, liveness_image.read_bytes(), "image/jpeg")},
    )
    liveness.raise_for_status()
    final = student.post(f"/attendance/attempts/{attempt_id}/finalize")
    final.raise_for_status()
    return {
        "face_status": face.json()["status"],
        "face_score": face.json()["score"],
        "liveness_status": liveness.json()["status"],
        "liveness_reason": liveness.json()["reason_code"],
        "liveness_provider": liveness.json()["provider"],
        "liveness_score": liveness.json()["score"],
        "decision": final.json()["decision"],
        "status": final.json()["status"],
        "reasons": [reason["code"] for reason in final.json()["reasons"]],
    }


def main() -> int:
    for path in (REFERENCE, FACE_PROBE, LIVE_PROBE, SPOOF_PROBE):
        if not path.is_file():
            print(f"Missing local test image: {path}", file=sys.stderr)
            return 2
    results: dict = {}
    with httpx.Client(base_url=BASE, timeout=60.0) as teacher:
        login(teacher, TEACHER)
        genuine_session = create_and_open(teacher)
        spoof_session = create_and_open(teacher)

    with httpx.Client(base_url=BASE, timeout=60.0) as student:
        login(student, STUDENT)
        enrollment = student.post(
            "/student/face-enrollment",
            data={"consent": "true", "consent_version": "liveness-check-v1"},
            files={"image": ("reference.png", REFERENCE.read_bytes(), "image/png")},
        )
        enrollment.raise_for_status()
        results["enrollment"] = enrollment.json()["status"]
        results["genuine"] = attempt(student, genuine_session, LIVE_PROBE)
        results["spoof"] = attempt(student, spoof_session, SPOOF_PROBE)
        deleted = student.delete("/student/face-enrollment")
        deleted.raise_for_status()
        results["deleted"] = deleted.json()["status"]

    print(json.dumps(results, indent=2))
    ok = (
        results["genuine"]["liveness_status"] == "PASSED"
        and results["genuine"]["decision"] == "ACCEPTED"
        and results["spoof"]["liveness_status"] == "FAILED"
        and results["spoof"]["decision"] == "REJECTED"
        and "LIVENESS_FAILED" in results["spoof"]["reasons"]
        and results["deleted"] == "deleted"
    )
    print("LIVE_LIVENESS_PASS" if ok else "LIVE_LIVENESS_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
