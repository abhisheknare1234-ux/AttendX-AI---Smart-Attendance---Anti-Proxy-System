# Product Requirements — AttendX AI

**Status:** implemented foundation for an institutional pilot. This document describes the product
intent and marks what is actually built; it is not a marketing specification.

## 1. Purpose

Provide an attendance verification product that makes common proxy paths materially harder than a
paper sheet, a static QR code or a shared link — while keeping legitimate student check-in quick and
keeping every decision explainable and reviewable by the teacher who owns the session.

## 2. Primary users

| Role | Needs | Typical device |
|---|---|---|
| Administrator | Provision authorized accounts, configure academics/policy/geofences, inspect audit/security, export reports | Desktop |
| Teacher | Open attendance only for assigned classes, display a rotating QR/PIN, monitor check-ins, review flagged evidence, correct records | Desktop |
| Student | Scan the classroom QR, prove the required factors, see an explicit result, review history, request review | Mobile browser |

## 3. Scope

**In scope:** identity and access management for the three roles; academic configuration; attendance
sessions; dynamic QR; temporary PIN; location evidence; provider-based face/liveness; duplicate and
replay prevention; deterministic risk decisions; teacher review; corrections; reports and CSV export;
audit/security events; CSV account import.

**Explicitly out of scope:** library, fees, hostel, transport, payroll, admissions, general ERP,
timetable optimization, continuous location tracking, automatic disciplinary action, and any claim of
100% proxy prevention.

## 4. Functional requirements and current status

### 4.1 Identity and access

| Requirement | Status | Evidence |
|---|---|---|
| Administrator bootstrap without hardcoded credentials | Implemented | `app/scripts/bootstrap_admin.py`, startup bootstrap via env |
| No public registration or self-assigned privileged roles | Implemented | No register endpoint; admin-only provisioning |
| Argon2id password hashing | Implemented | `app/core/security.py` |
| Server-managed sessions, HTTP-only cookie, revocation | Implemented | `AuthSession`, cookie configuration |
| Login rate limiting, account lockout, generic errors | Implemented | `services/auth.py`, tests |
| CSRF protection on mutating requests | Implemented | `require_csrf`, session-bound token |
| Role and resource authorization | Implemented | `core/deps.py`, assignment checks |
| Change own password; forced change for provisioned accounts | Implemented | `/auth/change-password`, `must_change_password` |

### 4.2 Academic configuration

| Requirement | Status |
|---|---|
| Classes, subjects, classrooms CRUD (create/update) | Implemented |
| Enrolments (bulk, duplicate-safe) | Implemented |
| Teacher assignments (class + optional subject, deactivation) | Implemented |
| Attendance policies (window, QR refresh, required factors, review behaviour) | Implemented |
| Geofences (classroom-anchored, radius, accuracy, outside-fix policy) | Implemented |
| CSV import with template, preview, validation, duplicates, transactional commit | Implemented |

### 4.3 Attendance session lifecycle

| Requirement | Status |
|---|---|
| Teacher creates a session only for an assigned class/subject | Implemented |
| Independent attendance window and QR refresh interval | Implemented |
| Open session generates PIN and first signed QR | Implemented |
| Server-authoritative close, PIN clearing, QR revocation | Implemented |
| Live counts and attempt statuses | Implemented (2-second polling) |

### 4.4 Student verification flow

| Requirement | Status |
|---|---|
| Native-camera QR entry and in-browser scanner | Implemented |
| QR token validated server-side; never marks attendance by itself | Implemented |
| PIN submission with attempt limit and rate limit | Implemented |
| Location evidence with explicit statuses (`INSIDE_GEOFENCE`, `OUTSIDE_GEOFENCE`, `LOW_ACCURACY`, `PERMISSION_DENIED`, `UNAVAILABLE`, `STALE`) | Implemented |
| Face verification | Implemented: local YuNet+SFace with encrypted templates and consent; external HTTP provider optional. Unconfigured = `UNAVAILABLE` |
| Liveness detection | Separate provider contract implemented; no liveness provider configured by default, reported `UNAVAILABLE` |
| Duplicate attendance prevention | Implemented with a database unique constraint |
| Final result with reference for accepted attendance | Implemented |

### 4.5 Review, reports, operations

| Requirement | Status |
|---|---|
| Automatic review queue for review-required attempts | Implemented |
| Student-initiated review requests | Implemented |
| Teacher resolution with note and correction history | Implemented |
| Attendance reports and CSV export | Implemented |
| Student history and subject summaries | Implemented |
| Audit and security event views | Implemented |
| Health/readiness and provider visibility | Implemented |
| In-lecture presence monitoring (BLE) | Data model only; not captured |
| Uniform detection | Not implemented |

## 5. Non-functional requirements

- **Security:** fail closed on missing/invalid evidence; never fabricate a verification success.
- **Privacy:** minimum necessary collection; no raw biometric images in attendance records; no
  continuous location history; evidence access restricted to authorized staff.
- **Auditability:** every administrative decision and attendance correction has an actor and time.
- **Responsiveness:** student experience is mobile-first with large touch targets; teacher live view
  remains usable on a tablet/desktop.
- **Performance (pilot scale):** session live view polling every 2 seconds; expected cohort sizes of
  tens to low hundreds per session. Load testing has not been run beyond the test suite.
- **Reliability:** database uniqueness prevents duplicate official records; provider outages degrade
  to review rather than silent failure.
- **Operability:** health endpoints, migrations, environment configuration, Compose definition.

## 6. Acceptance criteria

1. An unauthenticated user cannot reach admin/teacher/student data or perform attendance mutations.
2. A teacher cannot create or manage a session for a class they are not assigned to.
3. A student cannot check in twice for the same session; the database enforces one official record.
4. A QR token from a closed session, another session, or a tampered token is rejected.
5. A PIN beyond the attempt limit cannot be retried indefinitely; the attempt is rejected and
   reviewable.
6. An outside/low-accuracy/missing location result is not automatically labelled as dishonesty; it
   produces review or the configured policy outcome with reason codes.
7. If no face/liveness provider is configured, the result is `UNAVAILABLE` and no score is invented.
8. Accepted attendance returns a unique reference and appears in student history, teacher live counts
   and admin reports.
9. All admin configuration and review actions appear in the audit trail.
10. The project builds and the automated backend suite passes from a clean checkout.

## 7. Success measures for a pilot

- Legitimate check-in completion time and failure reasons.
- Teacher review rate and time-to-resolution.
- Duplicate-attendance attempts blocked.
- Provider availability and verification error rates.
- Student/teacher usability feedback and privacy complaints.
- **Not** “100% prevention”; the product must never be evaluated against an impossible claim.

## 8. Open decisions for the institution

- Which face/liveness provider is approved, its data-processing terms and threshold calibration.
- Consent wording, retention periods, deletion workflow and DPIA sign-off.
- Whether BLE presence hardware is available and supported on the student device fleet.
- Timetable integration and attendance percentage rules for the institution.
- Legal review under the Digital Personal Data Protection Act, 2023 and institutional policy.
