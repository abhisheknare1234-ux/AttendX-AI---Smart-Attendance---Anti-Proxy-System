# Test Plan and Actual Results — AttendX AI

## 1. Test environment

| Item | Value |
|---|---|
| Backend tests | Python 3.12.14, pytest 9.2.0, FastAPI 0.129.2, SQLAlchemy 2.0.57, in-memory SQLite (`StaticPool`) |
| Frontend | Node.js 24.22.1, Next.js 16.4.4, React 19.3.1, TypeScript 5.9.3 |
| Live integration | Uvicorn on `127.0.0.1:8000`, SQLite development database, seeded synthetic demo data |
| Web proxy check | `next start` on `127.0.0.1:3000`, API proxied through `/api/*` |
| Production build | `next build` (Turbopack) |
| Not available on the host | PostgreSQL server, Docker, Playwright browsers |

## 2. Backend automated suite

Command:

```bash
cd apps/api
pytest -q
```

**Actual result in this build: 37 passed in ~9 seconds.** (Warnings: one Starlette TestClient
deprecation warning.)

| File | Coverage |
|---|---|
| `test_auth.py` | Login/me/logout, generic wrong-password failures, 5-attempt lockout, CSRF enforcement, role denial, teacher cross-session access denied, password change, second student login |
| `test_qr_sessions.py` | Signature tamper/wrong key, valid/invalid token shape, open returns PIN+QR, live view, rotation, old-token grace, closed-session revocation, expired-token rejection |
| `test_attendance_flow.py` | Correct PIN advances attempt, five-wrong-PIN rejection + rejected record + duplicate block, full accepted flow, duplicate prevention, finalize-before-steps rejection, unenrolled student denied |
| `test_geofence_risk.py` | Haversine distance, inside/outside, low accuracy, stale, permission denied, unavailable; risk acceptance, outside/review vs reject, GPS missing → review, face unavailable → review, face mismatch → reject, liveness failure → reject, duplicate block, PIN failure, explainable reason shape |
| `test_reports_import.py` | Report totals/rows after a verified flow, CSV export, teacher class scoping, CSV preview validation, commit, temporary-password login, template |
| `conftest.py` | Isolated in-memory schema reset per seed, test-only academic fixture, CSRF-aware login helper |

### What the suite proves

- Authentication, session revocation and role boundaries.
- QR signing/expiry/rotation/revocation semantics.
- PIN attempt accounting and duplicate attendance prevention.
- Server-side geofence classification and deterministic risk decisions.
- Full check-in → finalize → record → dashboard/report propagation through the real HTTP stack.
- CSV validation and provisioning.

### What the suite does not prove

- PostgreSQL-specific behaviour (types, constraints, concurrency). SQLite is used for speed and host
  constraints.
- Real face/liveness provider behaviour, accuracy, fairness or anti-spoof quality.
- Browser camera/GPS permission flows under real device conditions.
- Load/performance, multi-process rate limiting, ingress/proxy IP forwarding.

## 3. Frontend verification

### Build

```bash
cd apps/web
npm run build
```

**Actual result: successful production build, 37 routes generated** (36 app routes + `_not-found`).
TypeScript checking completed inside the build. A separate `tsc --noEmit` also passed.

### Manual/proxy integration check

With the API seeded and running, a Python `httpx` client through `http://127.0.0.1:3000` verified:

- `GET /` returns 200 with the landing page.
- `GET /login` returns 200.
- `POST /api/v1/auth/login` through the Next rewrite sets cookies and returns a teacher session.
- `GET /api/v1/auth/me` and `GET /api/v1/teacher/classes` work through the proxy with the session.

### Not executed

- Playwright browser tests (browser binaries not installed on this host).
- Screenshot/visual regression tests.
- Real camera scanning and real browser geolocation prompts.

## 4. Live end-to-end flow

`scripts/live_flow_check.py` against a real Uvicorn process and seeded SQLite database:

| Step | Actual result |
|---|---|
| Teacher creates session for assigned class | 201, session UUID returned |
| Open session | 200, PIN and signed QR returned |
| Student validates QR | 200, session matches, can check in |
| Check-in | 201, attempt created, next step `pin` |
| PIN | `PASSED` |
| Location at classroom + ~15 m | `INSIDE_GEOFENCE`, distance 15.3 m |
| Finalize | `ACCEPTED`, `present`, `FULL`, reference `AX-…` |
| Duplicate check-in | `409 ALREADY_RECORDED` |
| Student dashboard | 1 held session, 1 attended |
| Teacher live view | 8 eligible, 1 accepted, 0 review |
| Admin report | 8 students, 1 session, 1 present |
| CSV export | `text/csv`, 817 bytes |
| Health | `ok`, database `ok`, providers `none` |

Result: **LIVE_FLOW_PASS**.

## 5. Security test checklist status

| Check | Status |
|---|---|
| Unauthorized access to admin endpoints | Automated |
| Teacher access to another teacher's session | Automated |
| CSRF missing on mutation | Automated |
| QR tamper/expiry/closed-session replay | Automated |
| Duplicate / concurrent finalize | Duplicate automated; concurrent stress not yet run |
| Login lockout | Automated |
| Rate limits | Login/PIN limits exercised indirectly; shared-store limits not tested |
| Input validation | Pydantic; malformed CSV/email tested; broader fuzzing not run |
| Origin enforcement | Implemented; not separately automated in the suite |
| Secret leakage | Manual review; secret scanning not configured |

## 6. How to extend the suite

1. Add PostgreSQL service in CI and run the same suite against a PostgreSQL URL.
2. Add `pytest-xdist`? No — concurrency tests should use explicit threads or a real DB.
3. Add Playwright with mocked camera/geolocation for the student flow and teacher live screen.
4. Add provider-contract tests against a local stub HTTP server (PASSED/FAILED/invalid/timeout).
5. Add load tests for live polling and check-in bursts.
6. Add `pip-audit` and `npm audit` to CI.
