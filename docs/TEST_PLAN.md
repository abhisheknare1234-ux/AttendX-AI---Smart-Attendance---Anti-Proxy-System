# Test Plan and Actual Results — AttendX AI

## 1. Test environment

| Item | Value |
|---|---|
| Backend tests | Python 3.12.14, pytest 9.2.0, FastAPI 0.129.2, SQLAlchemy 2.0.57, in-memory SQLite (`StaticPool`) **and real PostgreSQL 16.2** |
| Frontend | Node.js 24.22.1, Next.js 16.4.4, React 19.3.1, TypeScript 5.9.3 |
| Browser tests | Playwright 1.65.0, Chromium headless, live Next.js + FastAPI servers |
| Live integration | Uvicorn on `127.0.0.1:8000`, SQLite development database, seeded synthetic demo data |
| PostgreSQL | PostgreSQL 16.2 embedded test server on `127.0.0.1:5433`; migration DB + full-suite DB |
| Face models | OpenCV 4.14, YuNet 2023mar, SFace 2021dec; local sanity images not committed |
| Not available on the host | Docker; real mobile devices/cameras; production face/liveness evaluation data |

## 2. Backend automated suite

Command:

```bash
cd apps/api
pytest -q
```

**Actual result in this build: 42 passed in ~10 seconds** against SQLite, and **42 passed against
real PostgreSQL 16.2** using the same suite (`TEST_DATABASE_URL`). A Starlette TestClient
deprecation warning is the only warning.

The local face enrollment/match test is skipped when `FACE_TEST_MODEL_DIR`,
`FACE_TEST_IMAGE_REFERENCE` and `FACE_TEST_IMAGE_PROBE` are not supplied; with them it exercises the
real models. The other 41 tests do not require model binaries.

| File | Coverage |
|---|---|
| `test_auth.py` | Login/me/logout, generic wrong-password failures, 5-attempt lockout, CSRF enforcement, role denial, teacher cross-session access denied, password change, second student login |
| `test_qr_sessions.py` | Signature tamper/wrong key, valid/invalid token shape, open returns PIN+QR, live view, rotation, old-token grace, closed-session revocation, expired-token rejection |
| `test_attendance_flow.py` | Correct PIN advances attempt, five-wrong-PIN rejection + rejected record + duplicate block, full accepted flow, duplicate prevention, finalize-before-steps rejection, unenrolled student denied |
| `test_geofence_risk.py` | Haversine distance, inside/outside, low accuracy, stale, permission denied, unavailable; risk acceptance, outside/review vs reject, GPS missing → review, face unavailable → review, face mismatch → reject, liveness failure → reject, duplicate block, PIN failure, explainable reason shape |
| `test_reports_import.py` | Report totals/rows after a verified flow, CSV export, teacher class scoping, CSV preview validation, commit, temporary-password login, template |
| `test_biometrics.py` | Cosine similarity, encrypted template round-trip/tamper, honest missing-model state, consent enforcement, local enrollment/match/deletion when models and images are supplied |
| `conftest.py` | Isolated schema reset per seed, test-only academic fixture, CSRF-aware login helper, SQLite/PostgreSQL engine switch |

### What the suite proves

- Authentication, session revocation and role boundaries.
- QR signing/expiry/rotation/revocation semantics.
- PIN attempt accounting and duplicate attendance prevention.
- Server-side geofence classification and deterministic risk decisions.
- Full check-in → finalize → record → dashboard/report propagation through the real HTTP stack.
- CSV validation and provisioning.
- PostgreSQL schema compatibility (UUID, timestamptz, JSON, constraints) for the same tests.
- Encrypted face-template lifecycle, consent enforcement and genuine local embedding matching.

### PostgreSQL verification

- Alembic revision `64b3e63288ee` (baseline) and `7891b2a61c2a` (encrypted face templates) applied
  successfully to a fresh PostgreSQL database.
- `attendx_migrate` contains 26 tables including `alembic_version`; `biometric_enrollments` has
  `template_ciphertext` and `template_dimension`.
- The complete 42-test suite passed with `TEST_DATABASE_URL=postgresql+psycopg://…/attendx_test`.

### What the suite does not prove

- Real face/liveness provider accuracy, fairness or anti-spoof resistance. The local SFace check is
  a pipeline sanity test with a tiny sample, not an evaluation.
- Real browser camera/scanner capture on physical devices; browser tests mock geolocation and use
  the session-link path.
- Load/performance, multi-process rate limiting, ingress/proxy IP forwarding, backup/restore.

## 3. Frontend verification

### Build

```bash
cd apps/web
npm run build
```

**Actual result: successful production build, 37 routes generated** (36 app routes + `_not-found`).
TypeScript checking completed inside the build. A separate `tsc --noEmit` also passed.

### Manual/proxy integration check

With the API seeded and running, a Python `httpx` client through the web origin verified:

- `GET /` returns 200 with the landing page.
- `GET /login` returns 200.
- `POST /api/v1/auth/login` through the Next rewrite sets cookies and returns a teacher session.
- `GET /api/v1/auth/me` and `GET /api/v1/teacher/classes` work through the proxy with the session.

### Browser end-to-end (Playwright)

Command: `npx playwright test` from `apps/web`, with the API and web servers running.

**Actual result: 3 passed (9.0s).**

1. Administrator opens overview, users, policies, verification services and reports with real data.
2. Teacher creates a session for an assigned class, opens it, displays a signed QR/PIN, and a mobile
   student (390×844 viewport) logs in, opens the session link, enters the PIN, grants mocked
   geolocation, submits location, finalizes, and sees **Attendance confirmed** with an `AX-…`
   reference. The teacher's live accepted count updates to 1.
3. Student mobile shell shows bottom navigation and the scanner route with camera guidance.

Not executed in a real device browser: actual camera QR scanning, physical GPS accuracy variation,
and biometric capture UI.

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

### Live face-required flow

`scripts/live_face_check.py` against the API with `FACE_PROVIDER=local_opencv`:

| Step | Actual result |
|---|---|
| Student face enrollment with consent | `active`, provider `local_opencv`, model `sface-2021dec`, 128-D |
| Genuine probe (reflected reference) | cosine **0.947853**, `PASSED` / `FACE_MATCHED` |
| Finalize genuine attempt | `ACCEPTED`, `present`, reference `AX-…` |
| Impostor image | cosine **0.121694**, `FAILED` / `FACE_MISMATCH` |
| Finalize impostor attempt | `REJECTED`, `rejected`, reason `FACE_MISMATCH` |
| Delete enrollment | `deleted`; encrypted template cleared |

Result: **LIVE_FACE_PASS**. This proves the local embedding/matching pipeline works. It is **not** an
accuracy evaluation and does not cover liveness or presentation attacks.

## 5. Security test checklist status

| Check | Status |
|---|---|
| Unauthorized access to admin endpoints | Automated |
| Teacher access to another teacher's session | Automated |
| CSRF missing on mutation | Automated |
| QR tamper/expiry/closed-session replay | Automated |
| Duplicate / concurrent finalize | Duplicate automated; concurrent stress not yet run |
| Face template encryption + deletion | Automated |
| Face consent enforcement | Automated |
| Local face match quality (sanity) | Script and service test with real models/images |
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
