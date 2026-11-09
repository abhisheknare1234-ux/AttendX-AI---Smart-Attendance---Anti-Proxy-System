"""Face and liveness provider contracts.

No provider is configured by default. In that state verification is reported as
UNAVAILABLE — the system never fabricates a PASSED result, a confidence score or
a liveness decision.

Two face providers are available:

* ``http`` — an institution-approved external verification service.
* ``local_opencv`` — YuNet face detection plus the SFace 128-D recognizer from
  OpenCV Zoo, compared against an encrypted enrolled template. This is genuine
  local face matching. It is **not** liveness detection and does not claim
  presentation-attack resistance; configure a liveness provider for that.

Raw images are processed in memory and are never persisted by AttendX.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol, Sequence

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


@dataclass(slots=True)
class FaceEmbeddingResult:
    embedding: list[float] | None = None
    score: float | None = None
    reason_code: str | None = None
    provider: str = "local_opencv"
    model_version: str = "sface-2021dec"
    details: dict = field(default_factory=dict)


class FaceProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def verify(
        self,
        *,
        image: bytes,
        content_type: str,
        student_reference: str,
        reference_embedding: Sequence[float] | None = None,
    ) -> VerificationResult: ...


class LivenessProvider(Protocol):
    name: str

    @property
    def configured(self) -> bool: ...

    def check(self, *, image: bytes, content_type: str) -> VerificationResult: ...


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    import numpy as np

    a = np.asarray(left, dtype=np.float64)
    b = np.asarray(right, dtype=np.float64)
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denominator == 0.0:
        return 0.0
    return float(np.dot(a, b) / denominator)


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

    def verify(
        self,
        *,
        image: bytes,
        content_type: str,
        student_reference: str,
        reference_embedding: Sequence[float] | None = None,
    ) -> VerificationResult:
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

    def verify(
        self,
        *,
        image: bytes,
        content_type: str,
        student_reference: str,
        reference_embedding: Sequence[float] | None = None,
    ) -> VerificationResult:
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


class LocalOpenCvFaceProvider:
    """Genuine local face matching with OpenCV Zoo YuNet + SFace.

    The provider computes a normalized 128-dimensional embedding and compares it
    with the enrolled reference using cosine similarity. It reports FAILED only
    when a face was detected and the similarity is below the configured
    threshold; poor captures and ambiguous frames are reported as UNAVAILABLE so
    they can go to human review rather than being treated as identity mismatch.
    """

    name = "local_opencv"
    model_name = "opencv_sface"
    model_version = "sface-2021dec"

    _quality_reasons = {
        "FACE_DECODE_FAILED",
        "FACE_IMAGE_TOO_SMALL",
        "FACE_NOT_DETECTED",
        "FACE_MULTIPLE_DETECTED",
        "FACE_LOW_QUALITY",
        "FACE_EMBEDDING_FAILED",
    }

    def __init__(self, model_dir: str, match_threshold: float, detection_threshold: float) -> None:
        self._model_dir = Path(model_dir)
        self._match_threshold = match_threshold
        self._detection_threshold = detection_threshold
        self._lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._detector = None
        self._recognizer = None
        self._loaded = False
        self._load_error: str | None = None

    @property
    def detector_path(self) -> Path:
        return self._model_dir / "face_detection_yunet_2023mar.onnx"

    @property
    def recognizer_path(self) -> Path:
        return self._model_dir / "face_recognition_sface_2021dec.onnx"

    @property
    def configured(self) -> bool:
        return self.detector_path.is_file() and self.recognizer_path.is_file()

    def _ensure_models(self) -> bool:
        if self._loaded:
            return True
        with self._lock:
            if self._loaded:
                return True
            try:
                import cv2  # noqa: PLC0415 - optional local dependency
            except ImportError:
                self._load_error = "opencv is not installed"
                return False
            if not self.configured:
                self._load_error = "model files are missing"
                return False
            try:
                self._detector = cv2.FaceDetectorYN.create(
                    str(self.detector_path), "", (320, 320), self._detection_threshold, 0.3, 5000
                )
                self._recognizer = cv2.FaceRecognizerSF.create(str(self.recognizer_path), "")
            except Exception as exc:  # noqa: BLE001 - model boundary
                self._load_error = exc.__class__.__name__
                return False
            self._loaded = True
            return True

    def _embed(
        self, image: bytes, content_type: str
    ) -> tuple[list[float] | None, float | None, str | None, dict]:
        if not image:
            return None, None, "FACE_IMAGE_MISSING", {}
        if len(image) > 5 * 1024 * 1024:
            return None, None, "FACE_IMAGE_TOO_LARGE", {}
        try:
            import cv2  # noqa: PLC0415
            import numpy as np  # noqa: PLC0415
        except ImportError:
            return None, None, "FACE_ENGINE_UNAVAILABLE", {}

        array = np.frombuffer(image, dtype=np.uint8)
        decoded = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if decoded is None:
            return None, None, "FACE_DECODE_FAILED", {}
        height, width = decoded.shape[:2]
        if min(height, width) < 160:
            return None, None, "FACE_IMAGE_TOO_SMALL", {"width": width, "height": height}

        detector = self._detector
        recognizer = self._recognizer
        detector.setInputSize((width, height))
        _, faces = detector.detect(decoded)
        if faces is None or len(faces) == 0:
            return None, None, "FACE_NOT_DETECTED", {}
        if len(faces) > 1:
            return None, None, "FACE_MULTIPLE_DETECTED", {"faces": int(len(faces))}
        face = faces[0]
        quality = float(face[-1])
        if quality < self._detection_threshold:
            return None, quality, "FACE_LOW_QUALITY", {"detection_score": round(quality, 4)}
        try:
            aligned = recognizer.alignCrop(decoded, face)
            raw = recognizer.feature(aligned).flatten().astype(float).tolist()
        except Exception:  # noqa: BLE001 - model boundary
            return None, quality, "FACE_EMBEDDING_FAILED", {}
        if float(np.linalg.norm(np.asarray(raw, dtype=np.float64))) == 0.0:
            return None, quality, "FACE_EMBEDDING_FAILED", {}
        return raw, quality, None, {"detection_score": round(quality, 4)}

    def embed_reference(self, image: bytes, content_type: str) -> FaceEmbeddingResult:
        if not self.configured:
            return FaceEmbeddingResult(
                reason_code="LOCAL_FACE_MODELS_MISSING",
                details={"model_dir": str(self._model_dir), "load_error": self._load_error},
            )
        if not self._ensure_models():
            return FaceEmbeddingResult(
                reason_code="LOCAL_FACE_ENGINE_UNAVAILABLE",
                details={"load_error": self._load_error},
            )
        with self._infer_lock:
            embedding, quality, reason, details = self._embed(image, content_type)
        if embedding is None:
            return FaceEmbeddingResult(
                reason_code=reason,
                score=quality,
                details=details,
            )
        return FaceEmbeddingResult(
            embedding=embedding,
            score=quality,
            details={**details, "dimension": len(embedding)},
        )

    def verify(
        self,
        *,
        image: bytes,
        content_type: str,
        student_reference: str,
        reference_embedding: Sequence[float] | None = None,
    ) -> VerificationResult:
        if not self.configured:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LOCAL_FACE_MODELS_MISSING",
                provider=self.name,
                model_version=self.model_version,
                details={"model_dir": str(self._model_dir)},
            )
        if reference_embedding is None:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="FACE_NOT_ENROLLED",
                provider=self.name,
                model_version=self.model_version,
            )
        if not self._ensure_models():
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LOCAL_FACE_ENGINE_UNAVAILABLE",
                provider=self.name,
                model_version=self.model_version,
                details={"load_error": self._load_error},
            )

        embedding = None
        quality = None
        reason = None
        details = {}
        with self._infer_lock:
            embedding, quality, reason, details = self._embed(image, content_type)
        if embedding is None:
            status = (
                FactorStatus.UNAVAILABLE
                if reason in self._quality_reasons
                else FactorStatus.FAILED
            )
            return VerificationResult(
                status=status,
                score=None,
                reason_code=reason,
                provider=self.name,
                model_version=self.model_version,
                details=details,
            )

        similarity = cosine_similarity(reference_embedding, embedding)
        passed = similarity >= self._match_threshold
        return VerificationResult(
            status=FactorStatus.PASSED if passed else FactorStatus.FAILED,
            score=round(similarity, 6),
            reason_code="FACE_MATCHED" if passed else "FACE_MISMATCH",
            provider=self.name,
            model_version=self.model_version,
            details={
                **details,
                "cosine_similarity": round(similarity, 6),
                "threshold": self._match_threshold,
            },
        )


_QUALITY_LIVENESS_REASONS = {
    "LIVENESS_DECODE_FAILED",
    "LIVENESS_IMAGE_TOO_SMALL",
    "LIVENESS_NOT_DETECTED",
    "LIVENESS_MULTIPLE_FACES",
    "LIVENESS_LOW_QUALITY",
}


class LocalMiniFasLivenessProvider:
    """Single-frame passive anti-spoofing with MiniFASNet (Apache-2.0).

    The model is a binary Real/Spoof classifier over a padded 128x128 RGB crop.
    It is genuine texture-based anti-spoofing, not proof of a live person and not
    a challenge-response protocol. A no-face/poor capture is UNAVAILABLE; a
    detected face classified as spoof is FAILED; only a detected real face is
    PASSED. Raw images are never persisted.
    """

    name = "local_minifas"
    model_version = "minifas-128"

    def __init__(
        self,
        model_dir: str,
        detector_model_dir: str,
        threshold: float,
        detection_threshold: float,
    ) -> None:
        self._model_dir = Path(model_dir)
        self._detector_dir = Path(detector_model_dir)
        self._threshold = threshold
        self._detection_threshold = detection_threshold
        self._lock = threading.Lock()
        self._infer_lock = threading.Lock()
        self._session = None
        self._detector = None
        self._input_name: str | None = None
        self._loaded = False
        self._load_error: str | None = None

    @property
    def model_path(self) -> Path:
        return self._model_dir / "minifas_128.onnx"

    @property
    def detector_path(self) -> Path:
        candidate = self._detector_dir / "face_detection_yunet_2023mar.onnx"
        if candidate.is_file():
            return candidate
        return self._model_dir / "face_detection_yunet_2023mar.onnx"

    @property
    def configured(self) -> bool:
        return self.model_path.is_file() and self.detector_path.is_file()

    def _ensure_models(self) -> bool:
        if self._loaded:
            return True
        with self._lock:
            if self._loaded:
                return True
            if not self.configured:
                self._load_error = "model files are missing"
                return False
            try:
                import cv2  # noqa: PLC0415
                import onnxruntime as ort  # noqa: PLC0415
            except ImportError as exc:
                self._load_error = f"missing dependency: {exc.name}"
                return False
            try:
                session = ort.InferenceSession(
                    str(self.model_path), providers=["CPUExecutionProvider"]
                )
                self._detector = cv2.FaceDetectorYN.create(
                    str(self.detector_path), "", (320, 320), self._detection_threshold, 0.3, 5000
                )
                self._session = session
                self._input_name = session.get_inputs()[0].name
            except Exception as exc:  # noqa: BLE001 - model boundary
                self._load_error = exc.__class__.__name__
                return False
            self._loaded = True
            return True

    def _crop(self, image, bbox):  # noqa: ANN001
        import cv2  # noqa: PLC0415

        height, width = image.shape[:2]
        x, y, box_w, box_h = bbox
        longest = max(box_w, box_h)
        center_x, center_y = x + box_w / 2, y + box_h / 2
        size = max(1, int(longest * 1.5))
        x1, y1 = int(center_x - size / 2), int(center_y - size / 2)
        x2, y2 = x1 + size, y1 + size
        part = image[max(0, y1) : min(height, y2), max(0, x1) : min(width, x2)]
        return cv2.copyMakeBorder(
            part,
            max(0, -y1),
            max(0, y2 - height),
            max(0, -x1),
            max(0, x2 - width),
            cv2.BORDER_REFLECT_101,
        )

    def _letterbox(self, image, size: int = 128):  # noqa: ANN001
        import cv2  # noqa: PLC0415

        height, width = image.shape[:2]
        ratio = float(size) / max(height, width)
        new_w, new_h = max(1, int(width * ratio)), max(1, int(height * ratio))
        interpolation = cv2.INTER_LANCZOS4 if ratio > 1.0 else cv2.INTER_AREA
        resized = cv2.resize(image, (new_w, new_h), interpolation=interpolation)
        delta_w, delta_h = size - new_w, size - new_h
        return cv2.copyMakeBorder(
            resized,
            delta_h // 2,
            delta_h - delta_h // 2,
            delta_w // 2,
            delta_w - delta_w // 2,
            cv2.BORDER_REFLECT_101,
        )

    def _classify(self, image: bytes) -> tuple[float | None, float | None, str | None, dict]:
        try:
            import cv2  # noqa: PLC0415
            import numpy as np  # noqa: PLC0415
        except ImportError:
            return None, None, "LIVENESS_ENGINE_UNAVAILABLE", {}
        decoded = cv2.imdecode(np.frombuffer(image, dtype=np.uint8), cv2.IMREAD_COLOR)
        if decoded is None:
            return None, None, "LIVENESS_DECODE_FAILED", {}
        height, width = decoded.shape[:2]
        if min(height, width) < 160:
            return None, None, "LIVENESS_IMAGE_TOO_SMALL", {"width": width, "height": height}
        rgb = cv2.cvtColor(decoded, cv2.COLOR_BGR2RGB)
        detector = self._detector
        detector.setInputSize((width, height))
        _, faces = detector.detect(rgb)
        if faces is None or len(faces) == 0:
            return None, None, "LIVENESS_NOT_DETECTED", {}
        if len(faces) > 1:
            return None, None, "LIVENESS_MULTIPLE_FACES", {"faces": int(len(faces))}
        quality = float(faces[0][-1])
        if quality < self._detection_threshold:
            return None, quality, "LIVENESS_LOW_QUALITY", {"detection_score": round(quality, 4)}
        crop = self._letterbox(self._crop(rgb, faces[0][:4]))
        blob = (crop.transpose(2, 0, 1).astype(np.float32) / 255.0)[None]
        try:
            logits = self._session.run(None, {self._input_name: blob})[0][0]
        except Exception:  # noqa: BLE001 - model boundary
            return None, quality, "LIVENESS_ENGINE_UNAVAILABLE", {}
        real_logit, spoof_logit = float(logits[0]), float(logits[1])
        diff = real_logit - spoof_logit
        score = 1.0 / (1.0 + np.exp(-diff))
        passed = diff >= self._threshold
        return (
            float(score),
            quality,
            "LIVENESS_PASSED" if passed else "LIVENESS_SPOOF_DETECTED",
            {
                "real_logit": round(real_logit, 6),
                "spoof_logit": round(spoof_logit, 6),
                "logit_diff": round(diff, 6),
                "threshold": self._threshold,
                "detection_score": round(quality, 4),
            },
        )

    def check(self, *, image: bytes, content_type: str) -> VerificationResult:
        if not image:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LIVENESS_IMAGE_MISSING",
                provider=self.name,
                model_version=self.model_version,
            )
        if len(image) > 5 * 1024 * 1024:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LIVENESS_IMAGE_TOO_LARGE",
                provider=self.name,
                model_version=self.model_version,
            )
        if not self.configured:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LOCAL_LIVENESS_MODELS_MISSING",
                provider=self.name,
                model_version=self.model_version,
                details={"model_dir": str(self._model_dir)},
            )
        if not self._ensure_models():
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LOCAL_LIVENESS_ENGINE_UNAVAILABLE",
                provider=self.name,
                model_version=self.model_version,
                details={"load_error": self._load_error},
            )
        with self._infer_lock:
            score, quality, reason, details = self._classify(image)
        if reason is None:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code="LIVENESS_UNKNOWN_RESULT",
                provider=self.name,
                model_version=self.model_version,
            )
        if reason in _QUALITY_LIVENESS_REASONS:
            return VerificationResult(
                status=FactorStatus.UNAVAILABLE,
                reason_code=reason,
                provider=self.name,
                model_version=self.model_version,
                details=details,
            )
        passed = reason == "LIVENESS_PASSED"
        return VerificationResult(
            status=FactorStatus.PASSED if passed else FactorStatus.FAILED,
            score=round(float(score or 0.0), 6),
            reason_code=reason,
            provider=self.name,
            model_version=self.model_version,
            details={**details, "detection_score": quality},
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


_LOCAL_PROVIDERS: dict[tuple[str, float, float], LocalOpenCvFaceProvider] = {}
_LOCAL_PROVIDERS_LOCK = threading.Lock()


def get_face_provider(settings: Settings) -> FaceProvider:
    if settings.face_provider == "http":
        return HttpFaceProvider(
            settings.face_http_url, settings.face_http_token, settings.face_provider_model
        )
    if settings.face_provider == "local_opencv":
        key = (
            str(Path(settings.face_model_dir).expanduser().resolve()),
            float(settings.face_match_threshold),
            float(settings.face_detection_threshold),
        )
        with _LOCAL_PROVIDERS_LOCK:
            provider = _LOCAL_PROVIDERS.get(key)
            if provider is None:
                provider = LocalOpenCvFaceProvider(
                    key[0], key[1], key[2]
                )
                _LOCAL_PROVIDERS[key] = provider
            return provider
    return UnconfiguredFaceProvider()


_LIVENESS_PROVIDERS: dict[tuple[str, str, float, float], LocalMiniFasLivenessProvider] = {}
_LIVENESS_PROVIDERS_LOCK = threading.Lock()


def get_liveness_provider(settings: Settings) -> LivenessProvider:
    if settings.liveness_provider == "http":
        return HttpLivenessProvider(
            settings.liveness_http_url,
            settings.liveness_http_token,
            settings.liveness_provider_model,
        )
    if settings.liveness_provider == "local_minifas":
        key = (
            str(Path(settings.liveness_model_dir).expanduser().resolve()),
            str(Path(settings.face_model_dir).expanduser().resolve()),
            float(settings.liveness_threshold),
            float(settings.face_detection_threshold),
        )
        with _LIVENESS_PROVIDERS_LOCK:
            provider = _LIVENESS_PROVIDERS.get(key)
            if provider is None:
                provider = LocalMiniFasLivenessProvider(
                    key[0], key[1], key[2], key[3]
                )
                _LIVENESS_PROVIDERS[key] = provider
            return provider
    return UnconfiguredLivenessProvider()
