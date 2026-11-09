"""Biometric enrollment metadata responses. Templates and images are never returned."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models import BiometricStatus


class FaceEnrollmentOut(BaseModel):
    status: BiometricStatus
    provider: str
    model_name: str | None = None
    model_version: str | None = None
    consent_version: str | None = None
    consented_at: datetime | None = None
    deleted_at: datetime | None = None
    dimension: int | None = None
    local_face_available: bool = False
    liveness_provider: str = "none"
