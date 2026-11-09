# Known Limitations — AttendX AI

This list is deliberately explicit. A feature is not “working” because a screen exists.

## Verification and attendance

1. **Local face matching and optional local liveness are implemented, but liveness is `none` by
   default.** Face matching uses YuNet + SFace and encrypted templates. The optional MiniFASNet
   liveness provider is **single-frame passive anti-spoofing**, not a challenge-response protocol,
   and does not prove a live person is present. With no provider, liveness is `UNAVAILABLE`.
2. **Face and liveness accuracy/fairness are unevaluated.** The local sanity checks (face same
   identity 0.947853 / different identity 0.121694; liveness real 0.956488 / synthetic spoof
   0.354040) prove the pipelines work, not real-world error rates. No FAR/FRR, demographic, lighting,
   age or real presentation-attack evaluation has been performed.
3. **Liveness can be fooled by sophisticated presentation attacks**, 3D masks, deepfakes, camera
   injection or a modified client. The synthetic grayscale spoof check is not a real attack study.
4. **Enrollment is self-service with consent, without supervised identity proof or enrollment
   liveness.** A student could enroll a photo of another person; an institutional pilot should use
   supervised enrollment.
5. **No uniform detection** is implemented. It remains an optional, unauthorized research idea.
6. **BLE/presence monitoring is not captured.** The `presence_events` table and policy fields exist,
   but no beacon ingestion or presence-ratio classification is implemented. Final classification is
   currently FULL on acceptance, PENDING_REVIEW on review, INVALID on rejection, ABSENT on teacher
   absence marking.
7. **Initial check-in ≠ proof of remaining for the lecture.** Without presence monitoring, accepted
   attendance only reflects the verified check-in.
8. **Browser GPS and camera inputs are not tamper-proof.** A modified browser/OS can spoof location
   or feed a replayed image. These are evidence signals, not proof.
9. **PIN display is generation-only.** Because only an Argon2 hash is stored, a teacher who reloads
   the live page must regenerate the PIN to see it again. Students already verified are unaffected.

## Security and operations

1. **In-process rate limiting** is not shared across workers/instances.
2. **Client IP visibility:** when the API is reached only through the Next rewrite, per-IP limits may
   see the proxy address. Production ingress must forward/trust the real client IP.
3. **No staff MFA (WebAuthn/TOTP)** and **no password recovery flow**; administrators reset passwords.
4. **No automated retention/deletion job.** `EVIDENCE_RETENTION_DAYS` is configured but not enforced
    by a scheduler in this build.
5. **No shared cache/Redis**, no background job queue, no scheduled reports.
6. **No formal penetration test** has been performed. The threat model is design- and test-informed.
7. **OpenAPI docs are enabled** by default; restrict them at the ingress in production.
8. **Concurrent finalization** is protected by a unique constraint but has not been stress-tested
    against PostgreSQL.

## Data and deployment

1. **SQLite remains the default local profile; PostgreSQL is now validated.** The full suite passed
    against PostgreSQL 16.2 and both Alembic revisions applied, but high-concurrency/large-data
    behaviour was not load-tested.
2. **Docker/Compose was not runtime-verified** because Docker is unavailable on the development
    machine. The definitions are configuration-reviewed only.
3. **Alembic revisions apply to PostgreSQL**, including the encrypted-face-template migration; a
    backup/restore drill has not been performed.
4. **No automated backup job.** Backups are documented as an operational responsibility.
5. **No CI/CD pipeline** or secret scanning/dependency auditing is configured.

## Testing

1. **Browser end-to-end tests cover the desktop admin screens, teacher session lifecycle and a
    mobile student check-in with mocked geolocation.** Real camera scanning and physical-device GPS
    variation are still unverified.
2. **No visual regression/screenshot tests.**
3. **No load/performance tests** and no concurrency stress test.
4. **Face/liveness provider accuracy is not evaluated**; only the local SFace/YuNet pipeline was
    sanity-checked with a tiny sample. FACE_TEMPLATE_KEY rotation invalidates enrolled templates.

## Legal and institutional

1. **No claim of legal compliance.** Real biometric processing requires institutional authorization,
    consent, a DPIA and legal review, including under India's Digital Personal Data Protection Act,
    2023. The consent/deletion fields are engineering placeholders, not a compliance programme.
2. **No institutional data is included.** Synthetic demo data is development-only and contains no
    attendance records. Production requires authorized provisioning/CSV import.
3. **No institutional adoption is claimed.** The landing page describes a pilot-ready build.
