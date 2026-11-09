"""Authorized face enrollment and template lifecycle.

Only a 128-D embedding is stored, encrypted at rest. Images are processed in
memory and never persisted. Enrollment requires explicit consent and a local
provider that is actually configured.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import errors
from app.core.config import Settings
from app.core.template_crypto import TemplateCryptoError, decrypt_template, encrypt_template
from app.core.timeutil import utcnow
from app.models import BiometricEnrollment, BiometricStatus, StudentProfile
from app.providers.verification import LocalOpenCvFaceProvider, get_face_provider, get_liveness_provider
from app.schemas.biometrics import FaceEnrollmentOut
from app.services import audit as audit_service

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _local_provider(settings: Settings) -> LocalOpenCvFaceProvider:
    provider = get_face_provider(settings)
    if not isinstance(provider, LocalOpenCvFaceProvider):
        raise errors.bad_request(
            "Local face enrollment is only available when FACE_PROVIDER=local_opencv. "
            "External providers manage enrollment in their own service.",
            "FACE_ENROLLMENT_PROVIDER_EXTERNAL",
        )
    if not provider.configured:
        raise errors.bad_request(
            "The local face models are not installed on this deployment. Run the model download "
            "script and set FACE_MODEL_DIR.",
            "FACE_MODELS_MISSING",
        )
    return provider


def _row(db: Session, student_id: uuid.UUID) -> BiometricEnrollment | None:
    return db.scalar(
        select(BiometricEnrollment).where(BiometricEnrollment.student_id == student_id)
    )


def enrollment_out(db: Session, student_id: uuid.UUID, settings: Settings) -> FaceEnrollmentOut:
    provider = get_face_provider(settings)
    liveness = get_liveness_provider(settings)
    row = _row(db, student_id)
    if row is None:
        return FaceEnrollmentOut(
            status=BiometricStatus.NOT_ENROLLED,
            provider=provider.name,
            model_name=None,
            model_version=None,
            consent_version=None,
            consented_at=None,
            deleted_at=None,
            dimension=None,
            local_face_available=isinstance(provider, LocalOpenCvFaceProvider)
            and provider.configured,
            liveness_provider=liveness.name,
        )
    return FaceEnrollmentOut(
        status=row.status,
        provider=row.provider,
        model_name=row.model_name,
        model_version=row.model_version,
        consent_version=row.consent_version,
        consented_at=row.consented_at,
        deleted_at=row.deleted_at,
        dimension=row.template_dimension,
        local_face_available=isinstance(provider, LocalOpenCvFaceProvider) and provider.configured,
        liveness_provider=liveness.name,
    )


def enroll_face(
    db: Session,
    *,
    student_id: uuid.UUID,
    image: bytes,
    content_type: str,
    consent: bool,
    consent_version: str,
    settings: Settings,
    actor_user_id: uuid.UUID,
) -> FaceEnrollmentOut:
    if not consent:
        raise errors.bad_request(
            "Explicit consent is required before a face template can be created.",
            "FACE_CONSENT_REQUIRED",
        )
    version = consent_version.strip()[:32]
    if len(version) < 2:
        raise errors.bad_request("A consent version must be supplied.", "FACE_CONSENT_REQUIRED")
    if not image:
        raise errors.bad_request("A face image is required.", "FACE_IMAGE_MISSING")
    if len(image) > MAX_IMAGE_BYTES:
        raise errors.bad_request("The face image must be smaller than 5 MB.", "IMAGE_TOO_LARGE")
    if content_type not in ALLOWED_TYPES:
        raise errors.bad_request("Only JPEG, PNG or WebP images are accepted.", "UNSUPPORTED_IMAGE")

    provider = _local_provider(settings)
    result = provider.embed_reference(image, content_type)
    if result.embedding is None:
        raise errors.bad_request(
            "The enrollment image could not be used. Use a clear, front-facing photo with exactly "
            f"one face. Reason: {result.reason_code or 'UNKNOWN'}.",
            result.reason_code or "FACE_ENROLLMENT_REJECTED",
        )
    ciphertext = encrypt_template(
        result.embedding,
        model_name=provider.model_name,
        model_version=provider.model_version,
        settings=settings,
    )
    row = _row(db, student_id)
    now = utcnow()
    if row is None:
        row = BiometricEnrollment(
            student_id=student_id,
            provider=provider.name,
            model_name=provider.model_name,
            model_version=provider.model_version,
            status=BiometricStatus.ACTIVE,
            consent_version=version,
            consented_at=now,
        )
        db.add(row)
    else:
        row.provider = provider.name
        row.model_name = provider.model_name
        row.model_version = provider.model_version
        row.status = BiometricStatus.ACTIVE
        row.consent_version = version
        row.consented_at = now
        row.deleted_at = None
    row.template_ciphertext = ciphertext
    row.template_dimension = len(result.embedding)
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="FACE_ENROLLMENT_CREATED",
        entity_type="biometric_enrollment",
        entity_id=row.id,
        details={
            "provider": provider.name,
            "model": provider.model_name,
            "model_version": provider.model_version,
            "dimension": len(result.embedding),
            "consent_version": version,
        },
    )
    db.commit()
    db.refresh(row)
    return enrollment_out(db, student_id, settings)


def delete_face(
    db: Session,
    *,
    student_id: uuid.UUID,
    settings: Settings,
    actor_user_id: uuid.UUID,
) -> FaceEnrollmentOut:
    row = _row(db, student_id)
    if row is None:
        raise errors.not_found("No face enrollment exists for this student.")
    row.status = BiometricStatus.DELETED
    row.template_ciphertext = None
    row.template_dimension = None
    row.deleted_at = utcnow()
    audit_service.audit(
        db,
        actor_user_id=actor_user_id,
        action="FACE_ENROLLMENT_DELETED",
        entity_type="biometric_enrollment",
        entity_id=row.id,
        details={"provider": row.provider},
    )
    db.commit()
    return enrollment_out(db, student_id, settings)


def active_reference_embedding(
    db: Session, student_id: uuid.UUID, settings: Settings
) -> list[float] | None:
    row = _row(db, student_id)
    if row is None or row.status != BiometricStatus.ACTIVE or not row.template_ciphertext:
        return None
    try:
        payload = decrypt_template(row.template_ciphertext, settings)
    except TemplateCryptoError:
        return None
    embedding = payload.get("embedding")
    return [float(value) for value in embedding] if isinstance(embedding, list) else None


def has_active_enrollment(db: Session, student_id: uuid.UUID) -> bool:
    row = _row(db, student_id)
    return bool(
        row
        and row.status == BiometricStatus.ACTIVE
        and row.consented_at is not None
        and row.template_ciphertext
    )
