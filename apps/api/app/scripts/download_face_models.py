"""Download OpenCV/ONNX models for the local face and liveness providers.

Usage (from apps/api):
    python -m app.scripts.download_face_models
    python -m app.scripts.download_face_models --dir C:\\models

Models are not committed to the repository. This script verifies SHA-256 hashes.
The liveness model is the Apache-2.0 MiniFASNet-V2 classifier redistributed by the
facenox/face-antispoof-onnx project; review its licence/attribution before use.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

from app.core.config import get_settings

MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/"
        "face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/"
        "face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
    ),
    "minifas_128.onnx": (
        "https://raw.githubusercontent.com/facenox/face-antispoof-onnx/main/models/"
        "best_model_quantized.onnx",
        "fde20585635cae62ed1d41796f76b6f8bc4b92cd91ec1cf0f1bc6485d2d587a9",
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Download local face models")
    parser.add_argument("--dir", default=settings.face_model_dir)
    args = parser.parse_args()
    target_dir = Path(args.dir).expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    for filename, (url, expected) in MODELS.items():
        target = target_dir / filename
        if target.is_file():
            actual = _sha256(target)
            print(f"present {filename} sha256={actual}")
            if actual != expected:
                print(
                    f"ERROR: {filename} does not match the pinned SHA-256. "
                    "Remove it and review the model source.",
                    file=sys.stderr,
                )
                return 1
            continue
        print(f"downloading {url}")
        urllib.request.urlretrieve(url, target)
        actual = _sha256(target)
        print(f"downloaded {filename} bytes={target.stat().st_size} sha256={actual}")
        if actual != expected:
            target.unlink(missing_ok=True)
            print(
                f"ERROR: {filename} failed SHA-256 verification and was removed. "
                "The upstream model may have changed.",
                file=sys.stderr,
            )
            return 1
    print(f"models ready in {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
