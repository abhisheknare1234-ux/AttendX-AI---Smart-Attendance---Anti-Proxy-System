# AttendX AI

**Intelligent attendance with multi-factor verification and explainable trust.**

AttendX AI is an independently engineered attendance and anti-proxy verification product for
educational institutions. It combines a rotating, signed session QR code, a temporary PIN,
server-evaluated location evidence and configurable identity-provider checks into an auditable
backend decision — with a teacher review path when evidence is missing or borderline.

> **Build status:** a functional pilot-ready technical build, verified locally on SQLite and real
> PostgreSQL, with browser end-to-end tests. It is **not** a live campus deployment, not a complete
> college ERP, and it makes no claim of perfect proxy prevention or perfect biometric accuracy.
> Genuine local face matching is implemented with encrypted templates; it is **not** liveness.
> Liveness requires an institution-approved provider and is reported honestly as `UNAVAILABLE`
> when unconfigured.

## What is implemented and verified

| Area | Status |
|---|---|
| Administrator, teacher and student roles with backend RBAC | Implemented and tested |
| Argon2id passwords, locked accounts, server-managed sessions, HTTP-only cookies | Implemented and tested |
| CSRF-protected mutations, origin checks, security headers | Implemented and tested |
| Academic configuration: classes, subjects, classrooms, enrolments, assignments | Implemented |
| Dynamic signed QR with rotation, expiry, session binding and server validation | Implemented and tested |
| Temporary PIN with Argon2 hashing, attempt limits and invalidation on close | Implemented and tested |
| Server-side Haversine geofence with accuracy/staleness states | Implemented and tested |
| Duplicate attendance prevention and transactional record creation | Implemented and tested |
| Explainable risk engine with reason codes and review-required outcomes | Implemented and unit-tested |
| Teacher review queue and attendance corrections | Implemented |
| Student mobile flow: native-camera link, in-browser scanner, PIN, location, result | Implemented |
| CSV account import: template, preview, validation, duplicate detection, commit, audit | Implemented and tested |
| Reports, student history, subject summaries and CSV export | Implemented and tested |
| Audit and security event trails | Implemented |
| Face verification | Genuine local YuNet+SFace matching with consent, encrypted templates, deletion; external HTTP provider optional. `none` by default. Tested for enrollment/match/crypto |
| Liveness detection | Separate provider contract; **no liveness provider configured by default**, reported `UNAVAILABLE`. A face match is not liveness |
| PostgreSQL deployment path | Full 42-test suite executed against PostgreSQL 16.2; Alembic baseline + biometric migration applied |
| BLE presence monitoring | Schema/model only; not captured in this build |
| Uniform detection | Not implemented (optional research feature) |
| Scheduled automated backup job | Not included; documented operational requirement |

See [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md) for the complete honest boundary.

## Architecture

```text
Browser (desktop admin/teacher)        Browser (mobile student)
        │                                   │
        └──────────────┬────────────────────┘
                       ▼
              Next.js App Router (apps/web)
              • public landing, login, three workspaces
              • /api/* rewrite → FastAPI (same-origin cookies)
                       │
                       ▼
              FastAPI (apps/api)
              • auth + CSRF + RBAC
              • sessions / QR / PIN / location evidence
              • risk engine + reviews + reports
              • face/liveness provider adapters
                       │
                       ▼
              PostgreSQL (production) / SQLite (dev & tests)
              • 25 tables, Alembic migrations, audit trail
```

- **Modular monolith**, not microservices. One deployable API and one web app.
- **One database and one authorization model** serve both the desktop and mobile experiences.
- **Polling** (2 seconds on the teacher live view) is used instead of WebSockets; the pilot does not
  justify the extra operational surface.
- Production database is PostgreSQL. The local development/test profile uses SQLite because the
  development machine does not run Docker or PostgreSQL; this is documented rather than hidden.

## Repository layout

```text
attendx-ai/
  apps/
    api/
      app/
        api/v1/          # auth, admin, academic, teacher, student, attendance flow, reports, health
        core/            # config, db, security, deps, errors, rate limit
        models/          # SQLAlchemy models and enums
        schemas/         # Pydantic request/response contracts
        services/        # auth, attendance, QR/PIN logic, geofence, risk, reviews, reports, CSV
        providers/       # face and liveness provider contracts
        scripts/         # bootstrap_admin, seed_dev
      alembic/           # baseline migration
      tests/             # 42 pytest tests (SQLite and PostgreSQL)
    web/
      app/               # landing, login, admin, teacher, student, attend flow, account
      components/        # design system, shell, scanner, QR, check-in flow
      hooks/ lib/ public/
  docs/
  scripts/               # live_flow_check.py
  docker-compose.yml
  .env.example
```

## Local quick start

Requires Node.js 20+ and Python 3.11+ (verified on Node 24 and Python 3.12).

### 1. Backend

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

cp ../../.env.example .env      # edit SECRET_KEY and QR_SIGNING_KEY
# For SQLite development keep DATABASE_URL=sqlite:///./attendx_dev.db

# Create an administrator (never hardcoded; prompted password)
python -m app.scripts.bootstrap_admin --email admin@your-institution.ac.in --name "Administrator"

# Optional, development only: synthetic demo dataset (no attendance records)
python -m app.scripts.seed_dev --admin-password "..." --teacher-password "..." --student-password "..."

python -m uvicorn app.main:app --reload --port 8000
```

API docs: <http://127.0.0.1:8000/api/docs> · health: <http://127.0.0.1:8000/api/v1/health/ready>

### 2. Web

```bash
cd apps/web
npm install
npm run dev
```

Open <http://localhost:3000>. The web app proxies `/api/*` to `http://127.0.0.1:8000` by default.
Override with `API_INTERNAL_URL`.

### 3. Create a class and assignment

Sign in as the administrator, then use **Users / Students / Teachers** to provision accounts,
**Classes / Subjects / Classrooms** to configure academics, **Enrollments** to enrol students and
**Teacher assignments** to authorize a teacher. Then sign in as the teacher and start a session.

## Tests

```bash
cd apps/api
pytest -q
```

Verified in this build:

- **42 pytest tests passed** against isolated SQLite and, separately, against **real PostgreSQL
  16.2** with the same suite.
- **Alembic baseline + encrypted-face-template migration applied to PostgreSQL** (revision
  `7891b2a61c2a`, 26 tables including `alembic_version`).
- **`next build` succeeded**, with 37 routes.
- **3 Playwright browser tests passed** against live Next.js + FastAPI servers: administrator
  configuration screens; teacher session creation/opening and a complete mobile student check-in
  (PIN → browser geolocation → finalize → accepted reference); mobile student scanner navigation.
- **Live HTTP flow passed** against a real Uvicorn process: teacher creates/opens a session, student
  validates QR, enters PIN, submits location, finalizes, receives `ACCEPTED`/`present`/`FULL` with a
  unique reference; a duplicate check-in returns `409`; teacher live counts and admin reports reflect
  the record; CSV export returns `text/csv`.
- **Next.js proxy verified**: login, `/auth/me`, teacher classes and dashboard work through the web
  origin with cookies.
- **Local face provider validated end-to-end**: consent enrollment stored an encrypted 128-D
  template; a genuine reflected probe scored **0.947853 → PASSED** and finalized **ACCEPTED**; an
  impostor scored **0.121694 → FAILED** and finalized **REJECTED**; deletion cleared the template.
  These are pipeline sanity checks, not an accuracy evaluation. See
  [docs/FACE_VERIFICATION.md](docs/FACE_VERIFICATION.md).

Run the browser suite with the API and web servers running (web on `127.0.0.1:3000` and API
`WEB_ORIGIN` matching it):

```bash
cd apps/web
npx playwright test
```

## Environment and secrets

Copy `.env.example`; every value is a placeholder. Generate secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Never commit `.env`, database files, provider tokens or temporary passwords.

## Docker deployment

```bash
cp .env.example .env
# set POSTGRES_PASSWORD, SECRET_KEY, QR_SIGNING_KEY, WEB_ORIGIN, COOKIE_SECURE appropriately
docker compose up --build
```

The API container runs `alembic upgrade head` before starting. The web container serves the
production build. **Docker was not available on the development machine, so the Compose path is
configuration-verified but not runtime-verified.** See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

For local face verification, download the models on the API host and set
`FACE_PROVIDER=local_opencv`; the model files are not baked into the image:

```bash
cd apps/api
python -m app.scripts.download_face_models --dir /app/models
```

## Security summary

- Argon2id password hashing; account lockout; generic login failures.
- Server-side sessions with only a SHA-256 token hash persisted; HTTP-only, SameSite cookies.
- Session-bound CSRF token required for every mutating request.
- Role and resource checks on every teacher/student/admin endpoint.
- Signed, expiring, session-bound QR tokens; PIN hashed and invalidated on close.
- Optional local face templates are encrypted at rest (Fernet/HKDF), consent-gated, deletable and
  never returned by an API. Raw images are not persisted. Face matching is not liveness.
- No raw face images or biometric templates are stored by the core attendance record.
- Audit trail for provisioning, sessions, reviews, corrections, face enrollment/deletion and exports;
  security events for failed logins, lockouts, PIN failures and rejected attendance.
- No public registration or self-assigned privileged roles.

See [docs/SECURITY_AND_PRIVACY.md](docs/SECURITY_AND_PRIVACY.md) and
[docs/THREAT_MODEL.md](docs/THREAT_MODEL.md).

## Documentation

- [Product requirements](docs/PRODUCT_REQUIREMENTS.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database design](docs/DATABASE_DESIGN.md)
- [API contract](docs/API_CONTRACT.md)
- [Design system](docs/DESIGN_SYSTEM.md)
- [Dual UI architecture](docs/DUAL_UI_ARCHITECTURE.md)
- [Attendance workflow](docs/ATTENDANCE_WORKFLOW.md)
- [Face verification and liveness](docs/FACE_VERIFICATION.md)
- [Security and privacy](docs/SECURITY_AND_PRIVACY.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Reference project analysis](docs/REFERENCE_PROJECT_ANALYSIS.md)
- [Test plan and results](docs/TEST_PLAN.md)
- [Implementation roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [Third-party notices](docs/THIRD_PARTY_NOTICES.md)

## Licence

This repository is an independent project. No licence has been granted for reuse; add an explicit
licence before distributing or deploying it institutionally. The SnapClass reference projects are
all-rights-reserved and no code or assets from them are included.
