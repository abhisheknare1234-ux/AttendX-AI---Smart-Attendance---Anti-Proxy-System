"""Local anti-spoofing tests (optional model-dependent checks are skipped without models)."""
from __future__ import annotations

import os

import pytest

from app.models import FactorStatus
from app.providers.verification import LocalMiniFasLivenessProvider, get_liveness_provider
from app.core.config import Settings


def test_liveness_provider_without_models_is_unavailable(tmp_path):
    provider = LocalMiniFasLivenessProvider(
        str(tmp_path / "missing"), str(tmp_path / "missing"), 0.0, 0.7
    )
    assert provider.configured is False
    result = provider.check(image=b"not-an-image", content_type="image/jpeg")
    assert result.status == FactorStatus.UNAVAILABLE
    assert result.reason_code == "LOCAL_LIVENESS_MODELS_MISSING"


def test_liveness_provider_selection_is_explicit():
    settings = Settings(
        _env_file=None,
        app_env="test",
        secret_key="unit-test-secret",
        liveness_provider="none",
    )
    provider = get_liveness_provider(settings)
    assert provider.name == "none"
    assert provider.configured is False


def test_local_minifas_real_and_spoof_images():
    model_dir = os.environ.get("LIVENESS_TEST_MODEL_DIR", "").strip()
    real_image = os.environ.get("LIVENESS_TEST_REAL_IMAGE", "").strip()
    spoof_image = os.environ.get("LIVENESS_TEST_SPOOF_IMAGE", "").strip()
    if not (model_dir and real_image and spoof_image):
        pytest.skip("local liveness model/test images not provided")
    if not os.path.isdir(model_dir) or not os.path.isfile(real_image) or not os.path.isfile(spoof_image):
        pytest.skip("local liveness model/test images not found")

    provider = LocalMiniFasLivenessProvider(model_dir, model_dir, 0.0, 0.7)
    if not provider.configured:
        pytest.skip("local liveness models not installed")
    with open(real_image, "rb") as handle:
        real = provider.check(image=handle.read(), content_type="image/jpeg")
    with open(spoof_image, "rb") as handle:
        spoof = provider.check(image=handle.read(), content_type="image/jpeg")

    assert real.status == FactorStatus.PASSED, real
    assert real.score is not None and 0.0 <= real.score <= 1.0
    assert spoof.status == FactorStatus.FAILED, spoof
    assert spoof.reason_code == "LIVENESS_SPOOF_DETECTED"
