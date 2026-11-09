# Liveness and Anti-Spoofing

## 1. What is implemented

AttendX has three liveness deployment states:

| `LIVENESS_PROVIDER` | Behaviour |
|---|---|
| `none` (default) | Liveness is `UNAVAILABLE`; no success is fabricated |
| `http` | Calls an institution-approved external liveness service |
| `local_minifas` | Runs a local **single-frame passive anti-spoofing** classifier |

The local provider uses the Apache-2.0 **MiniFASNet-V2** binary Real/Spoof classifier redistributed
by [`facenox/face-antispoof-onnx`](https://github.com/facenox/face-antispoof-onnx), executed with
ONNX Runtime. It is a texture/frequency-based presentation-attack detector, not a challenge-response
protocol.

> A face match is **not** liveness detection. Liveness is evaluated as its own factor, and a
> spoof-detected capture is recorded as `FAILED` with `LIVENESS_SPOOF_DETECTED`.

## 2. Local pipeline

1. Decode the submitted image (JPEG/PNG/WebP, max 5 MB).
2. Detect exactly one face with OpenCV YuNet; no face or multiple faces → `UNAVAILABLE` for review,
   not a spoof accusation.
3. Crop a square around the face with 1.5× padding, letterbox to **128×128 RGB**, normalize to
   `[0,1]` and run the MiniFASNet ONNX classifier.
4. The model returns two logits: `real` and `spoof`.
5. `logit_diff = real - spoof`; `score = sigmoid(logit_diff)`.
6. `PASSED` when `logit_diff >= LIVENESS_THRESHOLD` (default `0.0`), otherwise `FAILED`.
7. Store only the status, score, logits, threshold and model version as verification evidence. Raw
   images are never persisted.

Failure/quality handling:

| Condition | Result |
|---|---|
| No image / too small / no face / multiple faces / low detection quality | `UNAVAILABLE` |
| Model or ONNX Runtime missing | `UNAVAILABLE` with a precise reason |
| Detected face classified as spoof | `FAILED` |
| Detected face classified as real | `PASSED` |

## 3. Evidence from this build

Live HTTP flow with `FACE_PROVIDER=local_opencv` and `LIVENESS_PROVIDER=local_minifas`:

| Step | Actual result |
|---|---|
| Enrollment | active, encrypted face template |
| Genuine portrait (real) | liveness `PASSED`, score **0.956488**, `LIVENESS_PASSED` |
| Face + liveness finalize | `ACCEPTED`, status `present`, `ALL_FACTORS_PASSED` |
| Print-like grayscale transform (synthetic spoof) | liveness `FAILED`, score **0.354040**, `LIVENESS_SPOOF_DETECTED` |
| Face + liveness finalize | `REJECTED`, status `rejected`, reason `LIVENESS_FAILED` |
| Enrollment deletion | `deleted` |

The spoof input was a **synthetic grayscale transform**, not a real printed/screen presentation
attack. This demonstrates the integration path and decision semantics; it is not a validated
anti-spoof evaluation.

## 4. Enabling it

```bash
cd apps/api
python -m app.scripts.download_face_models      # downloads YuNet, SFace and MiniFASNet with hash checks
```

```ini
FACE_PROVIDER=local_opencv
FACE_MODEL_DIR=models
FACE_TEMPLATE_KEY=<long random secret>
LIVENESS_PROVIDER=local_minifas
LIVENESS_MODEL_DIR=models
LIVENESS_THRESHOLD=0.0
```

`onnxruntime` is a runtime dependency (`requirements.txt`). Models are not committed.

## 5. Honest limitations

1. **Single-frame passive anti-spoofing is not proof of a live person.** It can be fooled by
   sophisticated presentation attacks, 3D masks, deepfakes, camera injection or a modified client.
2. **No challenge-response** (randomized action) or multi-frame temporal check is implemented. The
   upstream project recommends temporal filtering for video; AttendX currently evaluates one still.
3. **No independent evaluation.** The upstream project reports strong results on its own dataset,
   but this deployment has not measured false-accept/false-reject rates, demographic fairness,
   lighting robustness or real presentation attacks. The synthetic spoof check is only a sanity test.
4. **False rejects are possible**, especially in poor lighting, low resolution or with occlusions.
   The threshold is configurable; a stricter threshold increases false rejects.
5. **The institution must evaluate the provider** on consented, representative data and decide
   whether to enable it for high-stakes attendance decisions.
6. **Privacy/legal review is still required**; no claim of DPDP compliance is made.
