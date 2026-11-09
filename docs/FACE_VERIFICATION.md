# Face Verification and Liveness

## 1. Provider model

AttendX does not fabricate biometric results. Face verification has three deployment states:

| `FACE_PROVIDER` | Behaviour |
|---|---|
| `none` (default) | Every face step is `UNAVAILABLE`; no score and no success are invented |
| `http` | Calls an institution-approved external service implementing the documented contract |
| `local_opencv` | Runs genuine local matching with OpenCV Zoo YuNet + SFace models |

Liveness is always a separate contract (`LIVENESS_PROVIDER=none|http|local_minifas`). **A face match
is not liveness detection.** The optional local MiniFASNet single-frame anti-spoof classifier is
documented in [LIVENESS.md](LIVENESS.md); with no liveness provider the factor is `UNAVAILABLE` and
review policy applies.

## 2. Local matching pipeline

1. The student submits one image to `POST /student/face-enrollment` with explicit consent.
2. `cv2.FaceDetectorYN` (YuNet, 2023mar) detects faces. The image is rejected unless there is exactly
   one face with detection confidence at or above `FACE_DETECTION_THRESHOLD` (default 0.70) and the
   image is at least 160×160.
3. `cv2.FaceRecognizerSF` (SFace, 2021dec) aligns the face and computes a normalized 128-D embedding.
4. Only that embedding is stored, encrypted with Fernet (AES-128-CBC + HMAC-SHA256) under a key
   derived by HKDF from `FACE_TEMPLATE_KEY` (falling back to `SECRET_KEY`). The raw image is discarded.
5. During a face-required attendance step, the same pipeline embeds the new capture and computes
   cosine similarity against the decrypted reference.
6. Similarity at or above `FACE_MATCH_THRESHOLD` (default 0.363 for SFace) is `PASSED`; below is
   `FAILED` with the cosine score recorded. Poor captures (no face, multiple faces, too small,
   decode failure) are `UNAVAILABLE`, not identity mismatch, so they can be reviewed fairly.

Templates are never returned by an API and are not exposed to administrators. A student can delete
their template; deletion clears the ciphertext and records the deletion in the audit trail.

## 3. API

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/student/face-enrollment` | Status, provider/model, consent, dimension; never the template |
| POST | `/api/v1/student/face-enrollment` | Multipart `image`, `consent=true`, `consent_version`; encrypted enrollment |
| DELETE | `/api/v1/student/face-enrollment` | Soft delete and template ciphertext removal |

Enrollment is only accepted when `FACE_PROVIDER=local_opencv` and both model files are installed.
External providers manage enrollment in their own system; this API does not create templates for them.

## 4. Enabling local verification

```bash
cd apps/api
python -m app.scripts.download_face_models      # verifies pinned SHA-256 hashes
```

Set:

```ini
FACE_PROVIDER=local_opencv
FACE_MODEL_DIR=models
FACE_MATCH_THRESHOLD=0.363
FACE_DETECTION_THRESHOLD=0.7
FACE_TEMPLATE_KEY=<long random secret>
```

The model binaries are intentionally not committed. OpenCV Zoo model licences/terms must be
reviewed by the institution; see `THIRD_PARTY_NOTICES.md`.

## 5. Evidence from this build

A local sanity check was run with the real models and two public-domain/local test images (not
committed to the repository):

| Check | Result |
|---|---|
| Provider/model | `local_opencv` · `sface-2021dec` · 128-D |
| Reference detection quality | 0.9323 |
| Same identity, horizontally reflected (cosine) | **0.947853 → PASSED** at threshold 0.363 |
| Different identity (cosine) | **0.121694 → FAILED** at threshold 0.363 |

A live HTTP flow (`scripts/live_face_check.py`) then:

1. Enrolled the reference with consent through `POST /student/face-enrollment` → `active`, encrypted
   128-D template.
2. Created a face-required session, checked in, verified PIN and location, submitted the reflected
   probe, and finalized → **ACCEPTED**, status `present`, reference `AX-…`.
3. Created another face-required session and submitted an impostor image → **FAILED**
   (`FACE_MISMATCH`), finalized → **REJECTED**, status `rejected`.
4. Deleted the enrollment → `deleted`, template removed.

**These are pipeline sanity checks, not an accuracy evaluation.** The sample size is tiny. No
false-accept/false-reject rate, demographic fairness, age/lighting robustness or presentation-attack
evaluation has been performed. The institution must run a proper evaluation with consented data
before relying on biometric decisions.

## 6. Security and privacy limitations

- Enrollment is self-service with explicit consent; there is no independent liveness check at
  enrollment, so a student could enroll a photo of another person. An institution should require
  supervised enrollment for a real pilot.
- A printed photo or screen replay may pass face matching unless a **liveness provider** is also
  configured. Distance-only face verification must not be described as anti-spoofing.
- Template encryption protects at-rest database exposure, but the application process can decrypt
  templates by design. Database and application access must be tightly controlled.
- Rotating `FACE_TEMPLATE_KEY` (or relying on `SECRET_KEY` and rotating it) makes existing templates
  undecryptable; students must re-enroll.
- Retention and deletion obligations still require institutional policy and a DPIA; this build
  implements deletion of the local template but not provider-side deletion.
