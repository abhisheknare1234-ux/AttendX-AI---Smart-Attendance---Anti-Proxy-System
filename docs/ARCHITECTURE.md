# Architecture — AttendX AI

## 1. Architectural style

A **modular monolith** with two deployable processes:

1. `apps/api` — a FastAPI service owning authentication, authorization, attendance logic, risk
   evaluation, reports and audit.
2. `apps/web` — a Next.js App Router application providing the public landing page, login and two
   purpose-built interfaces (desktop staff workspace and mobile student journey).

One PostgreSQL database. No microservices, message broker, Redis or Kubernetes in this build. The
pilot scale does not justify them, and fewer moving parts make security review and operation easier.

## 2. Component view

```text
┌──────────────────────────── apps/web (Next.js) ────────────────────────────┐
│ Landing · Login · Admin workspace · Teacher workspace · Student mobile UI  │
│ /attend/[token] flow · Account security                                    │
│ Rewrite: /api/:path* → API_INTERNAL_URL/api/:path*                        │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ same-origin HTTP, cookies
┌───────────────────────────────────▼────────────────────────────────────────┐
│                         apps/api (FastAPI, sync SQLAlchemy)                │
│                                                                            │
│  Middleware        CORS · origin check · security headers · request id     │
│  Dependencies      get_current_auth · require_csrf · require_role          │
│  Routers           auth · academic · admin · teacher · student ·           │
│                    attendance flow · reports · health                      │
│  Services          auth · attendance · geofence · risk · reviews ·         │
│                    reports · CSV import · audit · users                    │
│  Providers         face (none/http) · liveness (none/http)                 │
│  Models            identity · academic · attendance · operations           │
└───────────────────────────────────┬────────────────────────────────────────┘
                                    │ SQLAlchemy 2.0
                        ┌───────────▼───────────┐
                        │ PostgreSQL (prod)     │
                        │ SQLite (dev / test)   │
                        └───────────────────────┘
```

## 3. Key request flows

### 3.1 Login

1. Browser posts email/password to Next rewrite → FastAPI `/api/v1/auth/login`.
2. API checks per-email/per-IP rate limits, account lock, Argon2id password.
3. On success it creates an `auth_sessions` row containing a SHA-256 hash of an opaque random token
   and a separate CSRF token, then sets:
   - `attendx_session` — HTTP-only, SameSite=Lax, Secure in staging/production;
   - `attendx_csrf` — readable by the app, same lifetime.
4. The response returns the user and CSRF token. The frontend routes by role.

### 3.2 Teacher session lifecycle

1. `POST /teacher/sessions` validates the teacher's active assignment for the class and subject,
   resolves the policy, snapshots required factors and window/refresh values, and stores a
   `scheduled` session.
2. `POST /teacher/sessions/{id}/open` requires ownership, opens the window from *now*, generates a
   cryptographic PIN (hashed with Argon2), creates the first signed QR token and audits the action.
3. `GET /teacher/sessions/{id}/live` returns an up-to-date QR (existing token or a newly rotated one),
   counts and recent attempts. The UI polls every two seconds.
4. `POST /close` changes the server state, revokes QR tokens, clears the PIN and abandons in-progress
   attempts. The frontend timer has no authority.

### 3.3 Student check-in and decision

```text
Scan / token
  → POST /attendance/qr/validate
      signature → server token row → expiry → session open → enrolment
  → POST /attendance/check-ins
      creates attempt (or returns the existing active attempt)
  → POST /attempts/{id}/pin        (verify Argon2 PIN, attempt limits)
  → POST /attempts/{id}/location   (Haversine, accuracy, staleness)
  → POST /attempts/{id}/face       (provider contract; UNAVAILABLE if unconfigured)
  → POST /attempts/{id}/liveness   (separate provider contract)
  → POST /attempts/{id}/finalize
      explainable risk engine → AttendanceRecord
      unique(session_id, student_id) prevents duplicates
      review-required → automatic ReviewRequest
```

All attempt operations verify that the attempt belongs to the authenticated student and that the
session is still open. Finalization is the only place an official attendance record is created.

## 4. Design decisions and trade-offs

| Decision | Rationale | Trade-off |
|---|---|---|
| Modular monolith | One authorization model, one transaction boundary, simple deployment | Fewer independent scaling options |
| Sync SQLAlchemy | Straightforward transactional logic and tests; FastAPI runs endpoints in a threadpool | Not suited to very high concurrency without tuning |
| Next rewrite for `/api` | Same-origin cookies, no browser CORS complexity, one origin for QR links | Backend sees the proxy address unless forwarded headers are configured |
| Polling (2 s) for live view | Reliable on institutional networks; no socket infrastructure | Slightly higher request rate; not instant |
| Provider abstraction for face/liveness | Institution chooses an approved provider; avoids faking a model | Requires procurement/configuration before those factors work |
| `UNAVAILABLE` routes to review | Missing evidence is not proof of cheating | More teacher review work when providers are down |
| SQLite for dev/test only | The development host has no Docker/PostgreSQL | Developer/production parity risk; mitigated by Alembic targeting PostgreSQL |
| Hash-only PIN storage + show-on-generation | Strong at-rest protection | Teacher must regenerate the PIN to display it after a page reload |

## 5. Data and transaction boundaries

- Session lifecycle and attempt mutations are committed atomically; the risk decision and
  `AttendanceRecord` are written in one transaction.
- A unique constraint on `(session_id, student_id)` is the final defence against duplicate official
  attendance, even under concurrent finalization.
- `IntegrityError` during finalization is treated idempotently: the existing record is returned.
- Audit/security events are appended in the same transaction as the action they describe (except
  standalone failed-login events, which commit immediately).

## 6. Security boundaries

- Browser: untrusted. QR tokens, PINs, GPS coordinates, images and claims are all untrusted input.
- API: the only decision authority. It validates signature, expiry, session state, ownership,
  enrolment, evidence states and policy.
- Provider: treated as untrusted output; only explicit `PASSED`/`FAILED` with optional bounded score
  is consumed. Network failures become `UNAVAILABLE`.
- Database: stores hashes for passwords/session tokens/PINs; no raw face images in attendance
  evidence; location coordinates are stored only for the attempt evidence/review.

## 7. Failure handling

| Failure | Behaviour |
|---|---|
| Database unavailable | Readiness reports degraded; requests fail with a generic 500 |
| QR expired/tampered | 400 with `QR_EXPIRED` / `QR_INVALID`; no attempt created |
| Session closed mid-flow | Finalization returns `SESSION_CLOSED`; no official record |
| PIN limit exceeded | Attempt rejected and a rejected record is created; visible for review |
| GPS permission denied | Recorded as evidence; risk engine → review (not automatic cheating) |
| Face/liveness provider down | `UNAVAILABLE`; review-required if the factor is mandatory |
| Duplicate finalize | Unique constraint + idempotent response |
| Lost teacher live view | Polling restores state from the database; no local authoritative state |

## 8. Scalability path (not implemented)

1. Replace the in-process rate limiter with a shared store and trust forwarded client IPs at the
   ingress.
2. Move live view to WebSockets or server-sent events if polling load becomes material.
3. Add read replicas/reporting jobs for large institutions.
4. Introduce object storage only if an approved provider requires evidence retention; never store raw
   biometrics in the primary record tables.
5. Split providers into independent services only when their operational needs justify it.

## 9. Repository map

| Path | Responsibility |
|---|---|
| `apps/api/app/core` | Configuration, database, security primitives, auth dependencies, errors, rate limit |
| `apps/api/app/models` | Identity, academic, attendance, operations tables and enums |
| `apps/api/app/services` | Domain logic: auth, users, attendance, geofence, risk, reviews, reports, import |
| `apps/api/app/providers` | Face/liveness contracts and optional HTTP adapters |
| `apps/api/app/api/v1` | HTTP routers |
| `apps/api/alembic` | Baseline migration |
| `apps/web/app` | Routes and role workspaces |
| `apps/web/components` | Design system, shell, QR display, camera scanner, check-in flow |
| `docs` | Architecture, security, API, testing, deployment, limitations |
