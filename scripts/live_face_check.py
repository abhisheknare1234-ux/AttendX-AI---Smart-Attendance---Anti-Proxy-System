"""Live face-required attendance check.

Requires the API to be running with:
    FACE_PROVIDER=local_opencv
    FACE_MODEL_DIR=<path containing the downloaded models>
    FACE_TEMPLATE_KEY=<key>

and a development database seeded with app.scripts.seed_dev. Test images are
local files; they are not committed and are processed only in memory.
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
PROBE = ROOT / ".cache" / "facedata" / "astronaut-flipped.jpg"
IMPOSTOR = ROOT / ".cache" / "facedata" / "opencv-messi.bin"


def login(client: httpx.Client, email: str, password: str) -> None:
    response = client.post("/auth/login", json={"email": email, "password": password})
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
            "require_liveness": False,
        },
    )
    created.raise_for_status()
    session = created.json()
    opened = client.post(f"/teacher/sessions/{session['id']}/open")
    opened.raise_for_status()
    payload = opened.json()
    payload["session_id"] = session["id"]
    return payload


def run_attempt(student: httpx.Client, opened: dict, face_path: Path, content_type: str) -> dict:
    checkin = student.post(
        "/attendance/check-ins", json={"qr_token": opened["qr"]["token"]}
    )
    checkin.raise_for_status()
    attempt_id = checkin.json()["attempt"]["id"]
    pin = student.post(
        f"/attendance/attempts/{attempt_id}/pin", json={"pin": opened["pin"]}
    )
    pin.raise_for_status()
    location = student.post(
        f"/attendance/attempts/{attempt_id}/location",
        json={
            "latitude": 18.5205,
            "longitude": 73.8568,
            "accuracy_m": 20,
            "client_timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    location.raise_for_status()
    face = student.post(
        f"/attendance/attempts/{attempt_id}/face",
        files={"image": (face_path.name, face_path.read_bytes(), content_type)},
    )
    face.raise_for_status()
    final = student.post(f"/attendance/attempts/{attempt_id}/finalize")
    final.raise_for_status()
    return {
        "attempt_id": attempt_id,
        "face_status": face.json()["status"],
        "face_reason": face.json()["reason_code"],
        "face_score": face.json()["score"],
        "decision": final.json()["decision"],
        "status": final.json()["status"],
        "reference": final.json()["reference"],
        "reasons": [reason["code"] for reason in final.json()["reasons"]],
    }


def main() -> int:
    for path in (REFERENCE, PROBE, IMPOSTOR):
        if not path.is_file():
            print(f"Missing local test image: {path}", file=sys.stderr)
            return 2
    results: dict = {}
    with httpx.Client(base_url=BASE, timeout=60.0) as teacher:
        login(teacher, *TEACHER)
        first = create_and_open(teacher)
        second = create_and_open(teacher)

    with httpx.Client(base_url=BASE, timeout=60.0) as student:
        login(student, *STUDENT)
        enrollment = student.post(
            "/student/face-enrollment",
            data={"consent": "true", "consent_version": "live-check-v1"},
            files={"image": ("reference.png", REFERENCE.read_bytes(), "image/png")},
        )
        enrollment.raise_for_status()
        results["enrollment"] = {
            "status": enrollment.json()["status"],
            "provider": enrollment.json()["provider"],
            "model": enrollment.json()["model_version"],
            "dimension": enrollment.json()["dimension"],
        }
        results["genuine_match"] = run_attempt(student, first, PROBE, "image/jpeg")
        results["impostor"] = run_attempt(student, second, IMPOSTOR, "image/jpeg")
        deleted = student.delete("/student/face-enrollment")
        deleted.raise_for_status()
        results["deleted_status"] = deleted.json()["status"]

    print(json.dumps(results, indent=2))
    ok = (
        results["enrollment"]["status"] == "active"
        and results["genuine_match"]["face_status"] == "PASSED"
        and results["genuine_match"]["decision"] == "ACCEPTED"
        and results["impostor"]["face_status"] == "FAILED"
        and results["impostor"]["decision"] == "REJECTED"
        and results["deleted_status"] == "deleted"
    )
    print("LIVE_FACE_PASS" if ok else "LIVE_FACE_FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
