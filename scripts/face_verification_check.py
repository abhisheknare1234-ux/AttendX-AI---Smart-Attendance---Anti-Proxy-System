"""Standalone local face-matching evidence check.

Usage:
    python scripts/face_verification_check.py \
      --model-dir apps/api/models \
      --reference path/to/reference.jpg \
      --probe path/to/probe.jpg \
      --impostor path/to/other-person.jpg

The images are processed locally and are not uploaded or stored. This is a
sanity check of the embedding/matching pipeline, not an accuracy evaluation.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from app.providers.verification import LocalOpenCvFaceProvider, cosine_similarity  # noqa: E402


def read_bytes(path: str) -> bytes:
    return Path(path).read_bytes()


def embed(provider: LocalOpenCvFaceProvider, path: str):
    result = provider.embed_reference(read_bytes(path), "image/jpeg")
    if result.embedding is None:
        raise SystemExit(f"Could not embed {path}: {result.reason_code}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Local face verification sanity check")
    parser.add_argument("--model-dir", default="apps/api/models")
    parser.add_argument("--threshold", type=float, default=0.363)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--probe", required=True)
    parser.add_argument("--impostor", required=True)
    args = parser.parse_args()

    provider = LocalOpenCvFaceProvider(args.model_dir, args.threshold, 0.7)
    if not provider.configured:
        print(f"Provider not configured. Missing models in {args.model_dir}.", file=sys.stderr)
        return 2

    reference = embed(provider, args.reference)
    probe = embed(provider, args.probe)
    impostor = embed(provider, args.impostor)
    probe_similarity = cosine_similarity(reference.embedding, probe.embedding)
    impostor_similarity = cosine_similarity(reference.embedding, impostor.embedding)
    print(
        {
            "provider": provider.name,
            "model_version": provider.model_version,
            "dimension": len(reference.embedding),
            "threshold": args.threshold,
            "reference_quality": reference.score,
            "same_identity_cosine": round(probe_similarity, 6),
            "same_identity_decision": "PASSED" if probe_similarity >= args.threshold else "FAILED",
            "different_identity_cosine": round(impostor_similarity, 6),
            "different_identity_decision": "PASSED" if impostor_similarity >= args.threshold else "FAILED",
        }
    )
    same_ok = probe_similarity >= args.threshold
    different_ok = impostor_similarity < args.threshold
    if not (same_ok and different_ok):
        print("CHECK_FAILED", file=sys.stderr)
        return 1
    print("CHECK_PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
