# Implementation Roadmap

Status legend: **Done**, **Partial**, **Not started**.

## Phase 0 — Research and architecture — Done

- Inspected the empty workspace and host constraints.
- Analysed the public SnapClass repositories and documented licensing/security observations.
- Defined architecture, data model, API groups, threat model and dual-UI route map.
- Documented the SQLite dev profile deviation from PostgreSQL.

## Phase 1 — Foundation — Done

- Next.js 16 App Router + TypeScript + Tailwind 4 design system.
- FastAPI + Pydantic v2 + SQLAlchemy 2 + Alembic.
- Health endpoints, database engine, environment configuration.
- Responsive landing, login split screen and role shells.

## Phase 2 — Authentication and authorization — Done

- Administrator bootstrap (CLI and optional startup env).
- Login, logout, `/auth/me`, password change, lockout, rate limits.
- Server-managed sessions, HTTP-only cookies, CSRF and origin checks.
- Role and resource checks; authorization tests.

## Phase 3 — Academic configuration — Done

- Users, students, teachers, classes, subjects, classrooms.
- Enrolments (bulk, duplicate-safe), teacher assignments.
- Attendance policies and geofences.
- CSV import template/preview/commit with row errors and audit.
- Admin UI pages for all of the above.

## Phase 4 — QR/PIN attendance — Done

- Teacher session creation with assignment validation and policy snapshot.
- Open/close, PIN generation/regeneration, signed rotating QR.
- Student validation, attempt creation, PIN verification, duplicate prevention.
- Live teacher view and counts.
- Tests for tamper, expiry, rotation, close, PIN limit and duplicates.

## Phase 5 — Dual UI — Done (browser E2E not automated)

- Administrator and teacher desktop workspaces.
- Mobile-first student home, scanner, attendance flow, history, subjects, reviews, profile.
- Native-camera URL entry and in-browser `jsQR` scanner.
- Next `/api` rewrite verified with cookies through a running server.

## Phase 6 — GPS — Done

- Browser geolocation with explicit explanations.
- Server-side Haversine distance, accuracy and staleness classification.
- Permission/unavailable evidence paths; risk review semantics.
- Geofence configuration UI/API.

## Phase 7 — Face verification — Partial (provider required)

- Provider protocol and HTTP adapter, enrollment/consent metadata model.
- Honest `UNAVAILABLE` when unconfigured/not enrolled.
- No bundled model, no threshold evaluation, no fabricated scores.
- **Next:** select and evaluate an institution-approved provider; calibrate thresholds; add a local
  stub for contract tests.

## Phase 8 — Liveness and risk engine — Partial (provider required for liveness)

- Separate liveness provider contract and status handling.
- Deterministic risk engine with reason codes, factor states, score points.
- Teacher review queue, student requests and corrections.
- **Next:** provider integration and evaluation; concurrency tests.

## Phase 9 — Presence monitoring — Not implemented (schema only)

- `presence_events` table and policy fields exist.
- No BLE beacon ingestion or final presence ratio calculation.
- **Next:** confirm hardware/device support, design classroom beacons, add presence ingestion and
  policy-based `FULL/PARTIAL/INTERRUPTED` computation.

## Phase 10 — Reports — Done

- Attendance reports by class/subject/date; teacher scoping.
- Student history and subject summaries.
- CSV export with audit event.
- **Next:** analytics trends, scheduled reports, longitudinal term comparisons.

## Phase 11 — Security and hardening — Partial

- Tests, audit/security trails, headers, validation, secrets separation.
- **Next:** PostgreSQL concurrency tests, shared rate limiting, trusted proxy IPs, staff MFA,
  password reset, dependency auditing, load tests, automated retention/deletion, DPIA.

## Phase 12 — Pilot preparation — Partial

- Documentation, tests, known limitations, deployment configuration.
- **Next:** end-to-end browser tests on real devices, institution-specific consent/policy, provider
  procurement, PostgreSQL staging deployment, backup/restore drill, pilot proposal.

## Immediate next highest-priority tasks

1. Run the full suite and application against **PostgreSQL** in staging (docker compose or managed
   Postgres).
2. Add Playwright e2e for teacher login → open → QR display and student scan/PIN/location/finalize.
3. Replace the in-process limiter with a shared store and forward real client IPs at the ingress.
4. Configure one approved face/liveness provider and run an evaluation before any real biometric use.
5. Add automated evidence-retention cleanup and a DPIA/consent package.
6. Add staff MFA and password reset.
7. Evaluate BLE hardware feasibility for presence monitoring.
