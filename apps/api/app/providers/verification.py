"""Face and liveness provider contracts.

No provider is configured by default. In that state verification is reported as
UNAVAILABLE — the system never fabricates a PASSED result, a confidence score or
a liveness decision.

The optional HTTP adapter integrates with any service that implements the
documented contract (see docs/VERIFICATION_PROVIDERS.md). It sends one image per
request and expects a small JSON response. Raw images are not persisted by
AttendX.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol

import httpx

from app.core.config import Settings
from app.models import FactorStatus

ProviderStatus = Literal["PASSED", "FAILED", "UNAVAILABLE", "ERROR"]


@dataclass(slots=True)
class VerificationResult:
    status: FactorStatus
    score: float | None = None
    reason_code: str | None = None
    provider: str = "none"
    model_version: str | None = None
    details: dict = field(default_factory=dict)


class FaceProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def verify(self, *, image: bytes, content_type: str, student_reference: str) -> VerificationResult: ...


class LivenessProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def check(self, *, image: bytes, content_type: str) -> VerificationResult: ...


class _UnconfiguredProvider:
    name = "none"
    configured = False

    def __init__(self, factor: str) -> None:
        self._factor = factor

    def _result(self, kind: str) -> VerificationResult:
        return VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code=f"{self._factor.upper()}_PROVIDER_NOT_CONFIGURED",
            provider="none",
            details={"message": f"No {kind} provider is configured on this deployment."},
        )


class UnconfiguredFaceProvider(_UnconfiguredProvider):
    def __init__(self) -> None:
        super().__init__("face")

    def verify(self, *, image: bytes, content_type: str, student_reference: str) -> VerificationResult:
        return self._result("face verification")


class UnconfiguredLivenessProvider(_UnconfiguredProvider):
    def __init__(self) -> None:
        super().__init__("liveness")

    def check(self, *, image: bytes, content_type: str) -> VerificationResult:
        return self._result("liveness")


class HttpFaceProvider:
    """Adapter for an institution-approved face verification service."""

    name = "http"

    def __init__(self, url: str, token: str, model_version: str) -> None:
        self._url = url
        self._token = token
        self._model_version = model_version

    @property
    def configured(self) -> bool:
        return bool(self._url)

    def verify(self, *, image: bytes, content_type: str, student_reference: str) -> VerificationResult:
        return _post_verification(
            url=self._url,
            token=self._token,
            files={"image": ("face.jpg", image, content_type or "image/jpeg")},
            data={"student_reference": student_reference},
            provider_name=self.name,
            model_version=self._model_version,
            factor="face",
        )


class HttpLivenessProvider:
    """Adapter for an institution-approved liveness detection service."""

    name = "http"

    def __init__(self, url: str, token: str, model_version: str) -> None:
        self._url = url
        self._token = token
        self._model_version = model_version

    @property
    def configured(self) -> bool:
        return bool(self._url)

    def check(self, *, image: bytes, content_type: str) -> VerificationResult:
        return _post_verification(
            url=self._url,
            token=self._token,
            files={"image": ("liveness.jpg", image, content_type or "image/jpeg")},
            data={},
            provider_name=self.name,
            model_version=self._model_version,
            factor="liveness",
        )


def _post_verification(
    *,
    url: str,
    token: str,
    files: dict,
    data: dict,
    provider_name: str,
    model_version: str,
    factor: str,
) -> VerificationResult:
    if not url:
        return VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code=f"{factor.upper()}_PROVIDER_NOT_CONFIGURED",
            provider=provider_name,
        )
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        with httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0)) as client:
            response = client.post(url, files=files, data=data, headers=headers)
    except httpx.HTTPError as exc:
        return VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code=f"{factor.upper()}_PROVIDER_UNREACHABLE",
            provider=provider_name,
            details={"error": exc.__class__.__name__},
        )

    if response.status_code >= 500:
        return VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code=f"{factor.upper()}_PROVIDER_ERROR",
            provider=provider_name,
            details={"http_status": response.status_code},
        )
    if response.status_code >= 400:
        return VerificationResult(
            status=FactorStatus.FAILED if response.status_code == 422 else FactorStatus.UNAVAILABLE,
            reason_code=f"{factor.upper()}_PROVIDER_REJECTED",
            provider=provider_name,
            details={"http_status": response.status_code},
        )

    try:
        payload = response.json()
    except ValueError:
        return VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code=f"{factor.upper()}_PROVIDER_INVALID_RESPONSE",
            provider=provider_name,
        )

    raw_status = str(payload.get("status", "")).upper()
    if raw_status not in {"PASSED", "FAILED"}:
        return VerificationResult(
            status=FactorStatus.UNAVAILABLE,
            reason_code=f"{factor.upper()}_PROVIDER_INVALID_STATUS",
            provider=provider_name,
            details={"provider_status": raw_status[:40]},
        )

    score = payload.get("score")
    if score is not None:
        try:
            score = float(score)
            if not (0.0 <= score <= 1.0):
                score = None
        except (TypeError, ValueError):
            score = None

    if raw_status == "PASSED" and score is None:
        # A pass without a score is accepted only when the provider explicitly
        # returns a pass; the absence of a score is recorded as null, never invented.
        pass

    return VerificationResult(
        status=FactorStatus.PASSED if raw_status == "PASSED" else FactorStatus.FAILED,
        score=score,
        reason_code=payload.get("reason_code"),
        provider=payload.get("provider") or provider_name,
        model_version=payload.get("model_version") or model_version,
        details={
            "provider_status": raw_status,
            "threshold": payload.get("threshold"),
        },
    )


def get_face_provider(settings: Settings) -> FaceProvider:
    if settings.face_provider == "http":
        return HttpFaceProvider(
            settings.face_http_url, settings.face_http_token, settings.face_provider_model
        )
    return UnconfiguredFaceProvider()


def get_liveness_provider(settings: Settings) -> LivenessProvider:
    if settings.liveness_provider == "http":
        return HttpLivenessProvider(
            settings.liveness_http_url,
            settings.liveness_http_token,
            settings.liveness_provider_model,
        )
    return UnconfiguredLivenessProvider()
