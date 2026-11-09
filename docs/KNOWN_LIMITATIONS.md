# Known Limitations — AttendX AI

This list is deliberately explicit. A feature is not “working” because a screen exists.

## Verification and attendance

1. **Local face matching is implemented but no liveness provider is configured.** Face matching uses
   YuNet + SFace and encrypted templates, but it does not detect presentation attacks. Liveness
   returns `UNAVAILABLE` until an approved provider is configured; no success is fabricated.
2. **Face accuracy and fairness are unevaluated.** The local sanity check (same identity 0.947853,
   different identity 0.121694 at threshold 0.363) proves the pipeline works, not its real-world
   error rates. No FAR/FRR, demographic, lighting, age or spoof evaluation has been performed.
3. **Enrollment is self-service with consent, without supervised identity proof or enrollment
   liveness.** A student could enroll a photo of another person; an institutional pilot should use
   supervised enrollment.
4. **No uniform detection** is implemented. It remains an optional, unauthorized research idea.
5. **BLE/presence monitoring is not captured.** The `presence_events` table and policy fields exist,
   but no beacon ingestion or presence-ratio classification is implemented. Final classification is
   currently FULL on acceptance, PENDING_REVIEW on review, INVALID on rejection, ABSENT on teacher
   absence marking.
6. **Initial check-in ≠ proof of remaining for the lecture.** Without presence monitoring, accepted
   attendance only reflects the verified check-in.
7. **Browser GPS and camera inputs are not tamper-proof.** A modified browser/OS can spoof location
   or feed a replayed image. These are evidence signals, not proof.
8. **PIN display is generation-only.** Because only an Argon2 hash is stored, a teacher who reloads
   the live page must regenerate the PIN to see it again. Students already verified are unaffected.

## Security and operations

7. **In-process rate limiting** is not shared across workers/instances.
8. **Client IP visibility:** when the API is reached only through the Next rewrite, per-IP limits may
   see the proxy address. Production ingress must forward/trust the real client IP.
9. **No staff MFA (WebAuthn/TOTP)** and **no password recovery flow**; administrators reset passwords.
10. **No automated retention/deletion job.** `EVIDENCE_RETENTION_DAYS` is configured but not enforced
    by a scheduler in this build.
11. **No shared cache/Redis**, no background job queue, no scheduled reports.
12. **No formal penetration test** has been performed. The threat model is design- and test-informed.
13. **OpenAPI docs are enabled** by default; restrict them at the ingress in production.
14. **Concurrent finalization** is protected by a unique constraint but has not been stress-tested
    against PostgreSQL.

## Data and deployment

15. **SQLite remains the default local profile; PostgreSQL is now validated.** The full suite passed
    against PostgreSQL 16.2 and both Alembic revisions applied, but high-concurrency/large-data
    behaviour was not load-tested.
16. **Docker/Compose was not runtime-verified** because Docker is unavailable on the development
    machine. The definitions are configuration-reviewed only.
17. **Alembic revisions apply to PostgreSQL**, including the encrypted-face-template migration; a
    backup/restore drill has not been performed.
18. **No automated backup job.** Backups are documented as an operational responsibility.
19. **No CI/CD pipeline** or secret scanning/dependency auditing is configured.

## Testing

20. **Browser end-to-end tests cover the desktop admin screens, teacher session lifecycle and a
    mobile student check-in with mocked geolocation.** Real camera scanning and physical-device GPS
    variation are still unverified.
21. **No visual regression/screenshot tests.**
22. **No load/performance tests** and no concurrency stress test.
23. **Face/liveness provider accuracy is not evaluated**; only the local SFace/YuNet pipeline was
    sanity-checked with a tiny sample. FACE_TEMPLATE_KEY rotation invalidates enrolled templates.

## Legal and institutional

24. **No claim of legal compliance.** Real biometric processing requires institutional authorization,
    consent, a DPIA and legal review, including under India's Digital Personal Data Protection Act,
    2023. The consent/deletion fields are engineering placeholders, not a compliance programme.
25. **No institutional data is included.** Synthetic demo data is development-only and contains no
    attendance records. Production requires authorized provisioning/CSV import.
26. **No institutional adoption is claimed.** The landing page describes a pilot-ready build.
