"""Biometric template crypto, consent and local-provider tests."""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import select

from app.core.config import Settings
from app.core.template_crypto import TemplateCryptoError, decrypt_template, encrypt_template
from app.models import BiometricEnrollment, BiometricStatus
from app.providers.verification import (
    FactorStatus,
    LocalOpenCvFaceProvider,
    cosine_similarity,
)
from tests.conftest import STUDENT_EMAIL, STUDENT_PASSWORD, login


def _settings(**overrides) -> Settings:
    values = {
        "app_env": "test",
        "secret_key": "unit-test-secret-key-for-face-templates",
        "qr_signing_key": "unit-test-qr-key",
        "face_template_key": "unit-test-face-template-key",
        "face_match_threshold": 0.363,
        "face_detection_threshold": 0.7,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_cosine_similarity():
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_template_encryption_roundtrip_and_tamper():
    settings = _settings()
    embedding = [0.1] * 128
    token = encrypt_template(
        embedding, model_name="opencv_sface", model_version="sface-2021dec", settings=settings
    )
    assert "0.1" not in token
    payload = decrypt_template(token, settings)
    assert payload["dim"] == 128
    assert len(payload["embedding"]) == 128
    with pytest.raises(TemplateCryptoError):
        decrypt_template(token[:-2] + "AA", settings)
    with pytest.raises(TemplateCryptoError):
        decrypt_template(token, _settings(face_template_key="different-key"))


def test_local_provider_without_models_is_honestly_unavailable(tmp_path):
    provider = LocalOpenCvFaceProvider(str(tmp_path / "missing"), 0.363, 0.7)
    assert provider.configured is False
    result = provider.verify(
        image=b"not-an-image",
        content_type="image/jpeg",
        student_reference="student",
        reference_embedding=[0.0] * 128,
    )
    assert result.status == FactorStatus.UNAVAILABLE
    assert result.reason_code == "LOCAL_FACE_MODELS_MISSING"


def test_face_enrollment_status_and_consent(client, seeded):
    login(client, STUDENT_EMAIL, STUDENT_PASSWORD)
    status = client.get("/api/v1/student/face-enrollment")
    assert status.status_code == 200
    assert status.json()["status"] == "not_enrolled"
    assert status.json()["provider"] == "none"

    rejected = client.post(
        "/api/v1/student/face-enrollment",
        data={"consent": "false", "consent_version": "v1"},
        files={"image": ("face.jpg", b"fake-image-bytes", "image/jpeg")},
    )
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "FACE_CONSENT_REQUIRED"


def test_local_enrollment_and_matching_if_models_available(seeded, db):
    model_dir = os.environ.get("FACE_TEST_MODEL_DIR", "").strip()
    image_path = os.environ.get("FACE_TEST_IMAGE_REFERENCE", "").strip()
    probe_path = os.environ.get("FACE_TEST_IMAGE_PROBE", "").strip()
    if not (model_dir and image_path and probe_path):
        pytest.skip("local face models/test images not provided")
    if not os.path.isdir(model_dir) or not os.path.isfile(image_path):
        pytest.skip("local face models/test images not found")

    from app.services.biometrics import (
        active_reference_embedding,
        delete_face,
        enroll_face,
        enrollment_out,
    )

    settings = _settings(face_provider="local_opencv", face_model_dir=model_dir)
    student_id = uuid.UUID(seeded["student_id"])
    actor_id = uuid.UUID(seeded["admin_id"])
    with open(image_path, "rb") as handle:
        image = handle.read()

    created = enroll_face(
        db,
        student_id=student_id,
        image=image,
        content_type="image/jpeg",
        consent=True,
        consent_version="pilot-v1",
        settings=settings,
        actor_user_id=actor_id,
    )
    assert created.status == BiometricStatus.ACTIVE
    assert created.dimension == 128
    reference = active_reference_embedding(db, student_id, settings)
    assert reference is not None and len(reference) == 128

    row = db.scalar(select(BiometricEnrollment).where(BiometricEnrollment.student_id == student_id))
    assert row is not None and row.template_ciphertext
    assert "embedding" not in row.template_ciphertext

    provider = LocalOpenCvFaceProvider(model_dir, settings.face_match_threshold, 0.7)
    with open(probe_path, "rb") as handle:
        probe = handle.read()
    matched = provider.verify(
        image=probe,
        content_type="image/jpeg",
        student_reference=str(student_id),
        reference_embedding=reference,
    )
    assert matched.status == FactorStatus.PASSED
    assert matched.score is not None and matched.score >= settings.face_match_threshold

    removed = delete_face(
        db,
        student_id=student_id,
        settings=settings,
        actor_user_id=actor_id,
    )
    assert removed.status == BiometricStatus.DELETED
    assert active_reference_embedding(db, student_id, settings) is None
    status = enrollment_out(db, student_id, settings)
    assert status.status == BiometricStatus.DELETED
