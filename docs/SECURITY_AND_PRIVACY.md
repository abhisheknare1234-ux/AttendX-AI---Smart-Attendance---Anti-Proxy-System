# Security and Privacy — AttendX AI

## 1. Security objectives

1. Only authorized, active accounts can use the system.
2. Only administrators can provision roles; only assigned teachers can open/manage sessions.
3. Students can see and act on their own attendance only.
4. Attendance decisions are made by the backend from recorded evidence, never by the client.
5. Secrets and biometric evidence are minimized, protected and not exposed by default.
6. Administrative and security-relevant actions are auditable.

## 2. Authentication

- **Passwords:** Argon2id (`argon2-cffi` defaults), unique salt per password.
- **Provisioning:** administrators create accounts; there is no public registration. Imported and
  provisioned users receive a one-time password and `must_change_password=true`.
- **Lockout:** five failed attempts lock the account for 15 minutes. Login failures are generic to
  avoid email enumeration; unknown-email attempts run a dummy Argon2 verification to reduce timing
  differences.
- **Rate limiting:** per-email and per-IP sliding windows for login, plus per-attempt PIN limits and a
  global per-IP request hint. The limiter is in-process and is documented as a pilot limitation.
- **Bootstrap:** `python -m app.scripts.bootstrap_admin` or environment variables; no credential is
  hardcoded. The bootstrap secret should be removed from the environment after first sign-in.

## 3. Sessions and cookies

- Opaque random session token (48 bytes) stored only as SHA-256 in `auth_sessions.token_hash`.
- Cookie `attendx_session`: HTTP-only, SameSite=Lax, `Secure` automatically in staging/production,
  path `/`, configurable TTL (default 8 h).
- CSRF token is a separate random value stored on the session row and mirrored in a readable
  `attendx_csrf` cookie. Every unsafe request must send it in `X-CSRF-Token`.
- Logout revokes the session row and clears cookies. Expired/revoked/disabled sessions are rejected.
- Long-lived tokens are never stored in local storage.

## 4. Authorization matrix

| Capability | Admin | Teacher | Student |
|---|---|---|---|
| Provision accounts, configure academics/policies/geofences | yes | no | no |
| View all audit/security events | yes | no | no |
| View verification provider status | yes | no | no |
| Create/open/close sessions | no (staff endpoints are teacher-scoped) | own assignments only | no |
| View live counts | no | own sessions | no |
| Resolve reviews/correct records | no | own sessions | no |
| Validate QR/check in | no | no | own enrolment only |
| View attendance history | all via reports | assigned classes | own only |
| Create review request | no | no | own sessions |

Resource checks are explicit in services/routers (session ownership, assignment membership, student
profile ownership). Admin endpoints do not expose password hashes or raw biometric data.

## 5. QR and PIN protections

- QR tokens are HMAC-SHA256 signed, session-bound, expiry-bound, nonce-tracked server-side and
  revoked on session close.
- Rotation keeps previous tokens valid only for their short configured lifetime, so legitimate
  scans in flight are not broken.
- The signed token string is not persisted; no long-lived QR secret is exposed.
- PINs are generated with `secrets`, hashed with Argon2id, attempt-limited, rate-limited, cleared on
  close and never logged. The PIN is returned only to the authenticated teacher at generation.

## 6. Evidence and provider security

- Face/liveness providers are optional adapters. Unavailable providers produce `UNAVAILABLE`, never a
  fabricated pass.
- Provider tokens are read from the environment and never returned by the API.
- AttendX stores verification metadata (status, optional score, provider, model version) and small
  location details, not image bytes.
- Provider responses are treated as untrusted: only explicit PASSED/FAILED with bounded score is
  consumed; malformed responses become unavailable.

## 7. Application hardening

- Request body validation by Pydantic; size limits on images (5 MB) and CSV (2 MB); MIME checks for
  images.
- Origin check for unsafe requests plus CSRF tokens.
- Security headers on both API and web (`nosniff`, frame deny, referrer policy, permissions policy).
- SQLAlchemy parameterization prevents SQL injection; no raw SQL built from user input.
- React escaping plus no `dangerouslySetInnerHTML` except locally generated QR SVG.
- Generic 500 responses; detailed exceptions only in server logs.
- Database uniqueness and transaction boundaries protect integrity.

## 8. Logging and audit

- Audit: provisioning, class/subject/room creation, assignments, enrolments, session create/open/
  close/PIN regeneration, review resolution, corrections, report export.
- Security events: unknown-email login, failed login, lockout, blocked inactive login, PIN failure,
  rejected attendance.
- Never logged: passwords, session tokens, PIN values, provider tokens, raw images.
- Session tokens are hashed; audit details contain identifiers, not secrets.

## 9. Privacy

### Data collected
Account identity and academic profile; attendance attempts/records; a single location fix per check-in
when permission is granted; optional provider verification outcomes; audit/security metadata.

### Not collected by default
Continuous location tracking; raw face galleries; background camera; microphone; unnecessary device
identifiers.

### Consent and legal review
Biometric enrollment metadata includes consent version and deletion state, but **this is not a
substitute for legal review**. Before real biometric processing the institution must obtain
authorization and consent, perform a DPIA, and review obligations under the Digital Personal Data
Protection Act, 2023 and applicable institutional policy. AttendX makes no claim of legal compliance.

### Retention
- Location evidence is tied to the attempt for review; `EVIDENCE_RETENTION_DAYS` (default 180) is
  configured but automated deletion is not included in this build.
- Session/auth/audit retention must be set institutionally.
- Biometric provider-side retention/deletion is an integration responsibility; the API supports a
  deleted status and consent records.

### Access
- Students see only their own records.
- Teachers see assigned classes/sessions; review evidence is limited to the session they own.
- Administrators see configuration and audit/security events, not biometric templates, raw images or
  provider credentials.
- Evidence details are intentionally not exposed on the public landing or login pages.

## 10. Known security limitations (must not be hidden)

1. The in-process rate limiter is not shared across multiple API workers/instances.
2. When the API is behind the Next rewrite, per-IP limiting may see the proxy address; production
   ingress must forward and trust the real client IP.
3. No automated evidence-retention/deletion job is included.
4. No WebAuthn/MFA for staff accounts; only password + session.
5. No password recovery flow; administrators reset passwords.
6. No CSRF-protected file-upload streaming limits beyond 2 MB CSV/5 MB image; large-body DoS controls
   belong at the ingress.
7. Face/liveness accuracy, spoof resistance and fairness are provider-dependent and have **not** been
   evaluated here; thresholds are not calibrated.
8. Browser GPS and camera inputs are not tamper-proof against a modified client.
9. OpenAPI docs are enabled by default; restrict them at the ingress for production.
10. SQLite is used for development/tests only; production must run PostgreSQL with backups and
    connection limits.
