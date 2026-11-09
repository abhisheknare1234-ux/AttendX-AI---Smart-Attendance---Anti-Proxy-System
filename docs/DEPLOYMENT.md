# Deployment — AttendX AI

## 1. Environments

| Environment | Database | Purpose |
|---|---|---|
| Development | SQLite (`DATABASE_URL=sqlite:///./attendx_dev.db`) | Local UI/backend work on a host without Docker/PostgreSQL |
| Test | In-memory SQLite (pytest) | Automated isolation |
| Staging | PostgreSQL 16 | Pilot rehearsal, browser/e2e, provider integration |
| Production | PostgreSQL 16 (managed or hardened) | Institutional pilot |

Production must run PostgreSQL and apply Alembic migrations. SQLite is not a production target.

## 2. Local development

### Backend

```bash
cd apps/api
python -m venv .venv
# activate
pip install -r requirements-dev.txt
cp ../../.env.example .env
# edit SECRET_KEY, QR_SIGNING_KEY; keep SQLite URL for local use
python -m app.scripts.bootstrap_admin --email admin@example.edu --name "Administrator"
python -m uvicorn app.main:app --reload --port 8000
```

The development app creates missing tables on startup. Apply migrations explicitly if you prefer
parity with production: `alembic upgrade head`.

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

`/api/*` is rewritten to `API_INTERNAL_URL` (default `http://127.0.0.1:8000`). This keeps cookies
same-origin, so no browser CORS configuration is needed.

### Optional demo seed

```bash
cd apps/api
APP_ENV=development python -m app.scripts.seed_dev \
  --admin-password "..." --teacher-password "..." --student-password "..."
```

Creates synthetic students/teacher/class/room/policy and **no attendance records**. Refuses to run
outside `APP_ENV=development`.

## 3. Docker Compose

```bash
cp .env.example .env
# Set at minimum:
#   POSTGRES_PASSWORD, SECRET_KEY, QR_SIGNING_KEY, WEB_ORIGIN
#   COOKIE_SECURE=true when served over HTTPS
docker compose up --build
```

Services:

- `db`: PostgreSQL 16 with a persistent volume and `pg_isready` health check.
- `api`: builds `apps/api`, runs `alembic upgrade head`, then Uvicorn on port 8000. Health check on
  `/api/v1/health/live`.
- `web`: builds `apps/web`, runs `next start` on port 3000, proxies `/api` to the API container.

**Verification status:** Docker was not available on the development host. The Compose and Dockerfile
definitions are configuration-reviewed but have not been executed. Treat the first staging run as a
deployment test, not a guaranteed path.

## 4. Production checklist

### Secrets and configuration

- [ ] Generate `SECRET_KEY` and a separate `QR_SIGNING_KEY` with a CSPRNG; store in a secret manager.
- [ ] Set `APP_ENV=production`; the app refuses the development secret.
- [ ] Set `DATABASE_URL` to PostgreSQL with a least-privilege application role.
- [ ] Set `WEB_ORIGIN` (and `ALLOWED_ORIGINS` if needed) to the exact HTTPS origin used in QR links.
- [ ] Set `COOKIE_SECURE=true`; terminate TLS before the web/API.
- [ ] Configure an approved face/liveness provider or leave it `none` and communicate that sessions
      requiring those factors will go to review.
- [ ] For local face/liveness: install the models with
      `python -m app.scripts.download_face_models --dir /app/models`, set `FACE_PROVIDER=local_opencv`
      and/or `LIVENESS_PROVIDER=local_minifas`, configure a strong `FACE_TEMPLATE_KEY`, and back up/
      rotate that key deliberately. Local liveness is single-frame anti-spoofing, not proof of a live
      person; evaluate it institutionally before relying on it.
- [ ] Remove `BOOTSTRAP_ADMIN_EMAIL/PASSWORD` after the first administrator exists.
- [ ] Disable or restrict `/api/docs` at the ingress if policy requires.

### Database

- [ ] Run `alembic upgrade head` as a release step.
- [ ] Enable automated backups and test a restore.
- [ ] Set connection limits and statement timeouts appropriate to the pilot.
- [ ] Plan evidence/audit retention and an automated deletion job (not included).
- [ ] Restrict network access to the database; no public port.

### TLS and reverse proxy

- [ ] HTTPS only; HSTS at the ingress after validation.
- [ ] Forward real client IP (`X-Forwarded-For`) and configure Uvicorn/proxy trust carefully.
- [ ] Keep the API private behind the web/ingress where possible; do not expose port 8000 publicly.
- [ ] Ensure the ingress body-size limits match the app limits (2 MB CSV, 5 MB image).
- [ ] Preserve `Set-Cookie` through the proxy and use the exact web origin.

### Verification providers

- [ ] Contract includes data-processing terms, retention and deletion.
- [ ] Provider endpoint reachable from the API; token stored server-side.
- [ ] Threshold and model version recorded; evaluation results documented.
- [ ] Failure/outage policy agreed with the institution (review vs reschedule).

### Operations

- [ ] Health checks monitored (`/api/v1/health/live`, `/health/ready`).
- [ ] Application logs aggregated; ensure no secrets/PINs/images are logged.
- [ ] Error tracking configured.
- [ ] Disk and database growth monitored.
- [ ] Incident response and secret rotation plan.

## 5. Backup and restore

Example PostgreSQL commands (adjust names/retention):

```bash
# backup
pg_dump --format=custom --file=attendx_$(date +%F).dump "$DATABASE_URL"

# restore into an empty database
pg_restore --clean --if-exists --dbname="$DATABASE_URL" attendx_2026-11-09.dump
```

Backups must be encrypted at rest, access-controlled and tested. Database dumps contain personal and
attendance data; treat them as sensitive.

## 6. Migrations and rollback

```bash
cd apps/api
alembic current
alembic upgrade head
alembic downgrade -1   # only if the migration is reversible and data loss is understood
```

Baseline migration: `64b3e63288ee`. Take a backup before every migration. Rollback of a schema
change does not restore deleted data.

## 7. Scaling notes

- Run multiple API workers only after replacing the in-process rate limiter with a shared store.
- Put the API behind an ingress that forwards client IPs; otherwise per-IP limits see the proxy.
- Live polling at 2 seconds is acceptable for pilot cohorts; revisit with WebSockets/SSE if needed.
- Reports are computed on demand; large institutions should add summary tables or scheduled jobs.
- SQLite is not suitable for multi-worker production.

## 8. What this deployment does not include

Kubernetes manifests, Redis, a message broker, object storage, CI/CD pipelines, a scheduled retention
job, automated certificate management, or a managed provider integration. These are deliberate
omissions, not hidden features.
