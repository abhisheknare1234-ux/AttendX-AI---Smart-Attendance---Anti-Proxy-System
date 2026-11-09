# Threat Model — AttendX AI

Scope: the attendance verification flow and its supporting accounts/configuration. This is a design
and test-informed model, not a penetration test of a production deployment.

**Residual-risk statement:** AttendX reduces common proxy paths. It cannot prove physical presence,
cannot make browser GPS or camera tamper-proof, and does not claim perfect biometric accuracy or
complete prevention of collusion.

| # | Threat | Scenario | Impact | Mitigation | Test evidence | Remaining limitation |
|---|---|---|---|---|---|---|
| 1 | Shared QR screenshot | Student forwards a QR to an absent friend who scans it later | Proxy attendance | Signed token bound to session, short expiry, rotation, live-session requirement; PIN + location + optional identity factors add independent checks | `test_qr_sessions.py::test_old_token_stays_valid_until_its_expiry_after_rotation`, expiry/closed-token tests | A friend in the room at the same time can still cooperate unless identity checks are required |
| 2 | PIN guessing | Attacker repeatedly submits six-digit PINs | Proxy attendance | Argon2 PIN, per-attempt limit (5), in-process rate limit, rejected record blocks fresh attempts, session-bound expiry | `test_attendance_flow.py::test_pin_attempt_limit_creates_rejected_record` | PIN space is small if an attacker could bypass the attempt/duplicate blocks; not a sole factor |
| 3 | Token theft / forgery | Attacker tampers with or fabricates a QR token | Unauthorized attempt | HMAC-SHA256 signature with server key, nonce row lookup, expiry, session status | `test_qr_sessions.py::test_qr_signature_tamper_rejected`, `test_invalid_token_rejected` | If the signing key leaks, tokens can be forged; rotate secrets |
| 4 | Replay after close | Student reuses a valid-looking token after the teacher closes | Stale attendance | Close revokes all tokens and clears PIN; validation/finalization check open state | `test_closed_session_invalidates_qr` | A token used before close but finalized just before closure is legitimate per policy |
| 5 | Duplicate requests | Double-click/submit or concurrent finalize creates two records | Inflated attendance | Unique `(session_id, student_id)`; idempotent finalize; existing-record check at check-in | `test_full_verified_flow_and_duplicate_prevention`, `test_pin_attempt_limit…` duplicate check | None at the database level for the same session/student |
| 6 | GPS spoofing | Modified client or developer tools reports classroom coordinates | False location evidence | Server-side distance/accuracy/staleness; GPS is evidence, not proof; review policy; optional identity checks | `test_geofence_risk.py` (inside/outside/low-accuracy/stale/permission) | Browser geolocation cannot be trusted against a tampered OS/browser; treat as a signal |
| 7 | Face-photo attack | Student holds a printed photo to the camera | Identity bypass | Provider must implement presentation-attack detection; AttendX does not claim its own liveness from a photo | Provider contract tests are not run without a provider | Entirely provider-dependent; no anti-spoof model is bundled |
| 8 | Video replay | Pre-recorded video played to the camera | Identity/liveness bypass | Liveness is a separate provider contract; pass/fail recorded honestly | No provider configured → `UNAVAILABLE` (verified in live flow only when required) | Provider must be evaluated against its own video-replay threat model |
| 9 | Liveness bypass | Simple blink/head-turn expected to defeat replay | False sense of security | Product does not implement or market a naive liveness method; unconfigured = `UNAVAILABLE` | Risk engine treats unavailable as review, not passed | Real liveness quality is unverified without an approved provider |
| 10 | Unauthorized access | Student/teacher accesses another role's endpoints or records | Data disclosure/modification | Session auth, role checks, ownership checks, enum-scoped queries, CSRF | `test_auth.py::test_student_cannot_access_admin`, `test_teacher_cannot_access_another_teachers_session` | Missing tests for every endpoint combination; review new routes carefully |
| 11 | Privilege escalation | User tries to register/assign a privileged role | Admin takeover | No registration endpoint; admin-only role creation; admin creation endpoint restricted to admins; no role change via PATCH | No registration route exists; CSRF/RBAC tests | A compromised admin session is game over; strong admin MFA is future work |
| 12 | Biometric data exposure | Admin or attacker reads face templates/images | Privacy harm | No raw images/templates in attendance records; provider metadata only; admin API exposes no biometrics; access limited | Provider status page and schemas show metadata only | Provider-side retention/security is external and must be contracted |
| 13 | Database compromise | Attacker reads the database | Credential/session/PIN exposure | Argon2id passwords and PINs; SHA-256 session token hashes; no plaintext tokens; secrets from environment | Code review of models/security | Argon2 hashes can be cracked if passwords are weak; rotate all secrets after a breach |
| 14 | Secret leakage | `.env`, logs, client bundle, repository | Full compromise | `.env` gitignored; provider tokens only server-side; no secrets in responses; no PIN/token logging | `.gitignore`, config review, API responses | Operator mistakes remain possible; secret scanning/rotation policies required |
| 15 | Race conditions | Parallel finalize/check-in requests | Duplicate or inconsistent records | Transactional finalize + unique constraint + idempotent paths; PIN counters increment transactionally | Duplicate flow test; design review; no automated concurrency stress test yet | SQLite tests do not prove PostgreSQL concurrency; add a concurrency test |
| 16 | Provider outage | Face/liveness service down | Blocked attendance or false rejections | `UNAVAILABLE` state, review routing, health visibility, no fabricated pass | Provider adapter code review; health endpoint | Review workload may spike; institution needs an outage policy |
| 17 | Session hijacking | Steal the session cookie | Account takeover | HTTP-only/SameSite/Secure cookies, token hash at rest, revocation, expiry | Cookie configuration review | No device-binding/rotation on privilege change; production needs HTTPS |
| 18 | CSRF | Malicious site submits attendance/config changes | Unauthorized action | Session-bound CSRF header + origin checks + SameSite | `test_csrf_required_for_mutations` | Same-site subdomain attacks remain possible; deploy carefully |

## Highest-priority residual risks

1. **Collusion in the same room** with identity factors disabled.
2. **Provider-dependent spoof resistance** (face/liveness) is unevaluated until procurement/calibration.
3. **Proxy IP visibility** affecting rate limiting when the API sits behind the Next rewrite.
4. **No institutional DPIA/consent** yet; biometric processing must not begin without it.
5. **No automated retention/deletion** for evidence and audit data.

## Recommended next security work

- Browser end-to-end tests with camera/location mocks and real Playwright runs.
- PostgreSQL concurrency test for finalization and PIN counters.
- Shared rate limiting (database/Redis) and trusted client-IP forwarding.
- Staff MFA (WebAuthn/TOTP), password reset with single-use tokens.
- Provider evaluation dataset and threshold calibration, including demographic error analysis.
- DPIA template, consent records and automated retention jobs.
- Secret scanning, dependency auditing (`pip-audit`, `npm audit`) and CI.
