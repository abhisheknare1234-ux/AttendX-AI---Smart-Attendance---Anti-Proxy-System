# Known Limitations — AttendX AI

This list is deliberately explicit. A feature is not “working” because a screen exists.

## Verification and attendance

1. **No face or liveness provider is configured by default.** Those factors return `UNAVAILABLE`.
   No bundled model, no confidence score, no success is fabricated. Provider accuracy, fairness and
   spoof resistance have not been evaluated here.
2. **No uniform detection** is implemented. It remains an optional, unauthorized research idea.
3. **BLE/presence monitoring is not captured.** The `presence_events` table and policy fields exist,
   but no beacon ingestion or presence-ratio classification is implemented. Final classification is
   currently FULL on acceptance, PENDING_REVIEW on review, INVALID on rejection, ABSENT on teacher
   absence marking.
4. **Initial check-in ≠ proof of remaining for the lecture.** Without presence monitoring, accepted
   attendance only reflects the verified check-in.
5. **Browser GPS and camera inputs are not tamper-proof.** A modified browser/OS can spoof location
   or feed a replayed image. These are evidence signals, not proof.
6. **PIN display is generation-only.** Because only an Argon2 hash is stored, a teacher who reloads
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

15. **SQLite is used for development and tests.** The production target is PostgreSQL, but the
    PostgreSQL path has not been executed on this host (no PostgreSQL, no Docker).
16. **Docker/Compose was not runtime-verified** because Docker is unavailable on the development
    machine. The definitions are configuration-reviewed only.
17. **Alembic baseline** was applied to SQLite; it has not been applied to a real PostgreSQL instance.
18. **No automated backup job.** Backups are documented as an operational responsibility.
19. **No CI/CD pipeline** or secret scanning/dependency auditing is configured.

## Testing

20. **No Playwright/browser e2e tests were executed**; browser binaries are not installed on this
    host. A live HTTP flow and the Next proxy were verified with `httpx` instead.
21. **No visual regression/screenshot tests.**
22. **No load/performance tests** and no concurrency stress test.
23. **Provider contract adapters are untested against a real provider** (no stub tests yet).

## Legal and institutional

24. **No claim of legal compliance.** Real biometric processing requires institutional authorization,
    consent, a DPIA and legal review, including under India's Digital Personal Data Protection Act,
    2023. The consent/deletion fields are engineering placeholders, not a compliance programme.
25. **No institutional data is included.** Synthetic demo data is development-only and contains no
    attendance records. Production requires authorized provisioning/CSV import.
26. **No institutional adoption is claimed.** The landing page describes a pilot-ready build.
