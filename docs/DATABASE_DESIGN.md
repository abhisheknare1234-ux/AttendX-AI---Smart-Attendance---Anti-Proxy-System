# Database Design — AttendX AI

## 1. Principles

- UUID primary keys (`Uuid` type; native UUID on PostgreSQL, 32-character hex on SQLite).
- All timestamps are UTC. A `TZDateTime` type decorator normalises writes to UTC and restores
  timezone awareness when SQLite drops it.
- String-backed enumerations (`VARCHAR`) with a length of 32 are used instead of native database
  enums, keeping migrations portable.
- JSON/JSONB-equivalent columns store reason codes and small evidence details, not unstructured
  blobs.
- Foreign keys and uniqueness constraints enforce the invariants that security depends on.
- No raw face images or biometric templates are stored in the attendance tables.
- 25 tables in four groups: identity, academic, attendance/verification, operations.

## 2. Entity overview

```text
users ─┬─ student_profiles ─── class_enrollments ─── classes ─── subjects
       │                               │                  │
       ├─ teacher_profiles ─── teacher_assignments ────────┘
       │                               │
       └─ auth_sessions                └─ attendance_sessions ─┬─ qr_tokens
                                                               ├─ attendance_attempts
                                                               │     ├─ verification_evidence
                                                               │     └─ review_requests
                                                               ├─ attendance_records
                                                               │     ├─ review_requests
                                                               │     └─ attendance_corrections
                                                               └─ presence_events

classrooms ── geofence_policies ── attendance_sessions
attendance_policies ────────────── attendance_sessions
biometric_enrollments ── student_profiles
audit_events / security_events / import_jobs / app_settings (operational)
```

## 3. Identity

### `users`
| Column | Notes |
|---|---|
| `id` | UUID primary key |
| `email` | unique, indexed, lower-cased by the service |
| `password_hash` | Argon2id string, never returned by any API |
| `role` | `admin` / `teacher` / `student` |
| `full_name`, `phone` | display/contact |
| `status` | `active` / `disabled` / `locked` |
| `must_change_password` | true for provisioned/imported accounts |
| `failed_login_count`, `locked_until` | progressive lockout |
| `last_login_at`, `created_at`, `updated_at` | UTC |

### `student_profiles`
Unique `user_id` and `roll_number`; department, programme, year, division, batch, admission year.

### `teacher_profiles`
Unique `user_id` and `employee_id`; department, designation.

### `auth_sessions`
Opaque server session: `token_hash` (SHA-256, unique) and `csrf_token`; IP/user-agent metadata;
`expires_at`; `revoked_at`. Raw session tokens never touch the database.

## 4. Academic

| Table | Key constraints | Purpose |
|---|---|---|
| `academic_terms` | unique `name` | Optional term scoping for classes |
| `classes` | unique `code`; indexed `name` | Cohort (department/year/division) |
| `subjects` | unique `code`; FK `class_id` | Subject taught to one class |
| `classrooms` | unique `code` | Coordinates + geofence defaults |
| `class_enrollments` | unique `(class_id, student_id)` | Eligibility for sessions |
| `teacher_assignments` | unique `(teacher_id, class_id, subject_id)`; indexed FKs | Authorization to open sessions |
| `geofence_policies` | unique `name`; optional `classroom_id` | Centre, radius, accuracy, outside-fix policy |
| `attendance_policies` | unique `name`; at most one default (application-enforced) | Window, QR refresh, required factors, review policy |

## 5. Attendance and verification

### `attendance_sessions`
The authorization and policy snapshot for one lecture.

- FKs: `class_id`, `subject_id`, `classroom_id`, `teacher_id`, `policy_id`, `geofence_id`,
  `created_by_id`, `closed_by_id`.
- `status`: `scheduled` → `open` → `closed` / `expired` / `cancelled`.
- Snapshot columns: `window_seconds`, `qr_refresh_seconds`, `qr_grace_seconds`, four `require_*`
  booleans, `allow_review_outside_geofence`.
- PIN: `pin_hash`, `pin_expires_at` (never plaintext).
- Times: `starts_at`, `ends_at`, `opened_at`, `closed_at`, `created_at`, `updated_at`.

### `qr_tokens`
One row per rotation: `session_id`, unique `nonce`, `issued_at`, `expires_at`, `revoked_at`. The
signed token string is **not** stored; it is reconstructed from these fields with HMAC. Multiple
tokens can be valid concurrently, so rotation does not invalidate another student's scan.

### `attendance_attempts`
The working check-in state for a student/session.

- Unique `reference`; FKs to session, student, QR token.
- Factor states: `qr_status`, `pin_status`, `gps_status`, `face_status`, `liveness_status`.
- `pin_attempts`, `current_step`, `gps_distance_m`, `gps_accuracy_m`, `gps_recorded_at`,
  `gps_submitted_at`.
- Decision: `risk_score`, `risk_decision`, `risk_reasons` (JSON), timestamps.
- Indexed by session, student, status.

### `verification_evidence`
Append-only evidence rows per attempt/factor: status, optional score, reason code, provider,
model version, small JSON details (distance/accuracy/coordinates). No image bytes.

### `attendance_records`
The official result.

- **Unique `(session_id, student_id)`** — the hard defence against duplicate attendance.
- Unique `reference`; optional unique `attempt_id`.
- `status`: present / absent / review_required / rejected.
- `classification`: FULL / PARTIAL / INTERRUPTED / INVALID / ABSENT / PENDING_REVIEW.
- `decision_source`: system / teacher; `decided_by_id`, `decided_at`, `check_in_at`, `remarks`.

### `presence_events`
Designed for optional in-lecture proximity/BLE evidence: session, student, event type, source,
occurred_at, JSON details. The table and model exist; no BLE ingestion is implemented in this build.

## 6. Operations, review and biometric metadata

| Table | Purpose / constraints |
|---|---|
| `review_requests` | Student or system review case; status open/approved/rejected/withdrawn; record/attempt links |
| `attendance_corrections` | Immutable old→new status/classification with actor and reason |
| `audit_events` | Append-only administrative actions, actor, entity, JSON details, IP |
| `security_events` | Login/PIN/attendance security signals with severity |
| `biometric_enrollments` | Consent metadata, provider/model version, encrypted face template ciphertext and dimension; **no raw images** |
| `import_jobs` | CSV import summary and row errors |
| `app_settings` | Key/JSON value settings table (seeded/used by future configuration UI) |

## 7. Indexes and uniqueness

- Unique: user email; roll number; employee ID; class/subject/classroom codes; policy names; session
  `(class, student)` enrolment; teacher assignment scope; QR nonce; attempt reference; record
  reference; session `(session_id, student_id)`.
- Indexed: foreign keys used in authorization and reporting, plus status columns used by dashboards
  and live views.
- Partial uniqueness for “one active attempt” is enforced in service logic (not a partial index), so
  the rule is explicit and portable.

## 8. Transactions and concurrency

- Session create/open/close and attempt mutations use one SQLAlchemy session per request.
- Finalization writes the record and updates the attempt in the same transaction. The unique
  constraint resolves races; on `IntegrityError` the transaction is rolled back and the existing
  record is returned idempotently.
- PIN attempt counters are incremented transactionally; the in-process limiter is an additional
  guard, not the sole limit.

## 9. Retention and deletion (designed, not automated)

- Raw images: never persisted by AttendX; the provider is responsible for its own retention.
- Verification evidence JSON includes coordinates for review; retention is a configuration
  requirement (`EVIDENCE_RETENTION_DAYS`, default 180) and must be enforced by a scheduled job in a
  production deployment.
- Biometric enrollment supports a `deleted_at` state and consent version; actual provider-side
  deletion is an integration responsibility.
- Audit/security events are intended to be retained per institutional policy; deletion must preserve
  legal obligations.

## 10. Migrations

```bash
cd apps/api
alembic upgrade head          # apply
alembic current               # show revision
alembic history               # list
```

Baseline revision: `64b3e63288ee` (`initial attendance schema`).
Second revision: `7891b2a61c2a` (`encrypted face templates`) adds
`biometric_enrollments.template_ciphertext` and `template_dimension`.

Both revisions were applied successfully to **real PostgreSQL 16.2** in this build (26 tables in the
migration database including `alembic_version`; 25 runtime tables). The same operations also target
SQLite for development. The migrations use standard `sa.Uuid`, `sa.String`, `sa.DateTime(timezone=True)`,
`sa.Text` and `sa.JSON` types.

**Face template storage:** only a 128-D embedding is persisted, encrypted with Fernet
(AES-128-CBC + HMAC-SHA256) under an HKDF-derived key. Raw enrollment/capture images are not stored.
The column is nullable so deletion can clear it while retaining an audit record.

The development profile creates tables directly on startup as a convenience. **Production must run
Alembic**; the API container does so before Uvicorn starts.
