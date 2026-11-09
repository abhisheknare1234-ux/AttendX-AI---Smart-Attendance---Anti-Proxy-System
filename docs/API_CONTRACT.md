# API Contract — AttendX AI v1

Base path: `/api/v1` (the web app proxies `/api/*` to the API). OpenAPI: `/api/docs`.

## 1. Authentication and request conventions

- Login creates an HTTP-only session cookie (`attendx_session`) and a readable CSRF cookie
  (`attendx_csrf`).
- Every **mutating** request (POST/PATCH/DELETE) from an authenticated session must send
  `X-CSRF-Token: <csrf_token>` matching the server-side session. Missing/invalid → `403 CSRF_FAILED`.
- Requests with an `Origin` header must match the configured allowed origins.
- All timestamps are ISO-8601 with a timezone; the server normalises to UTC.
- Error shape:

```json
{
  "error": {
    "code": "VERIFICATION_PENDING",
    "message": "Required verification steps are still pending.",
    "details": { "next_step": "gps" }
  }
}
```

- Validation errors return `422` with `error.code = VALIDATION_ERROR` and a list of field errors.
- Rate-limited responses return `429` and `retry_after_seconds`.

## 2. Auth

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | public (origin-checked) | `{email,password}` → `{user, csrf_token}` and cookies |
| POST | `/auth/logout` | session + CSRF | Revokes the session and clears cookies |
| GET | `/auth/me` | session | Current user and CSRF token |
| POST | `/auth/change-password` | session + CSRF | `{current_password,new_password}` |

Provisioned accounts have `must_change_password=true`. There is no registration endpoint.

## 3. Shared academic read

| Method | Path | Roles |
|---|---|---|
| GET | `/classes` | all authenticated (role-scoped) |
| GET | `/subjects?class_id=` | all authenticated (role-scoped) |
| GET | `/classrooms` | all authenticated |
| GET | `/geofences` | staff |
| GET | `/policies` | staff |

## 4. Administrator

All routes require role `admin` and CSRF for mutations.

| Method | Path | Description |
|---|---|---|
| GET/POST | `/admin/users` | List accounts; create administrator accounts (role must be admin) |
| PATCH | `/admin/users/{id}` | Name, status, forced password change, password reset |
| GET/POST | `/admin/students` | List/create student accounts |
| GET/POST | `/admin/teachers` | List/create teacher accounts |
| GET/POST/PATCH | `/admin/classes`, `/admin/classes/{id}` | Classes |
| GET/POST/PATCH | `/admin/subjects`, `/admin/subjects/{id}` | Subjects |
| GET/POST/PATCH | `/admin/classrooms`, `/admin/classrooms/{id}` | Classrooms |
| GET/POST | `/admin/enrollments` | List; bulk enrol `{class_id,student_ids[]}` |
| DELETE | `/admin/enrollments/{id}` | Drop enrolment |
| GET/POST | `/admin/assignments` | List/create teaching assignments |
| DELETE | `/admin/assignments/{id}` | Deactivate assignment |
| GET/POST/PATCH | `/admin/policies`, `/admin/policies/{id}` | Attendance policies |
| GET/POST | `/admin/geofences` | Geofences |
| GET | `/admin/audit-logs` | Append-only audit trail (`action`, `limit`, `offset`) |
| GET | `/admin/security-events` | Security events (`severity`, pagination) |
| GET | `/admin/imports/template?kind=students|teachers` | CSV template |
| POST | `/admin/imports/preview` | Multipart `kind` + `file`; row-level validation |
| POST | `/admin/imports/commit` | Multipart; transactional creation, one-time passwords returned |

## 5. Teacher

| Method | Path | Description |
|---|---|---|
| GET | `/teacher/dashboard` | Counts, recent sessions, review queue |
| GET | `/teacher/profile`, `/teacher/classes`, `/teacher/subjects`, `/teacher/students` | Assigned scope |
| POST | `/teacher/sessions` | Create a session (assignment validated) |
| GET | `/teacher/sessions?status=&limit=` | Own sessions |
| GET | `/teacher/sessions/{id}` | Session detail |
| POST | `/teacher/sessions/{id}/open` | Open; returns `pin`, `pin_expires_at`, first `qr` |
| POST | `/teacher/sessions/{id}/close` | Close; revokes QR and PIN |
| POST | `/teacher/sessions/{id}/qr` | Rotate and return a new QR |
| POST | `/teacher/sessions/{id}/pin/regenerate` | New PIN (displayed once) |
| GET | `/teacher/sessions/{id}/live` | Session counts, current QR, recent attempts |
| GET | `/teacher/reviews?status=` | Review queue |
| POST | `/teacher/reviews/{id}/resolve` | `{decision: approved|rejected, note, mark_present?}` |
| POST | `/teacher/records/{id}/correction` | `{new_status,new_classification?,reason}` |

### Session create request

```json
{
  "class_id": "uuid",
  "subject_id": "uuid",
  "classroom_id": "uuid",
  "starts_at": "2026-11-09T09:30:00+05:30",
  "window_seconds": 180,
  "qr_refresh_seconds": 30,
  "policy_id": "uuid-or-null",
  "geofence_id": "uuid-or-null",
  "require_pin": true,
  "require_geofence": true,
  "require_face": false,
  "require_liveness": false
}
```

### Open response (abridged)

```json
{
  "session": { "id": "uuid", "status": "open", "ends_at": "…", "accepted": 0 },
  "pin": "482913",
  "pin_expires_at": "…",
  "qr": {
    "token": "v1.<payload>.<signature>",
    "url": "http://localhost:3000/attend/v1.…",
    "expires_at": "…",
    "refresh_seconds": 30
  }
}
```

## 6. Student attendance flow

All require role `student` and CSRF for mutations.

| Method | Path | Description |
|---|---|---|
| POST | `/attendance/qr/validate` | `{token}` → session summary, requirements, `can_check_in`; verifies enrolment |
| POST | `/attendance/check-ins` | `{qr_token}` → creates/returns an attempt, `required_steps`, `next_step` |
| GET | `/attendance/attempts/{id}` | Own attempt + session summary + next step |
| POST | `/attendance/attempts/{id}/pin` | `{pin}` |
| POST | `/attendance/attempts/{id}/location` | `{latitude, longitude, accuracy_m, client_timestamp?, permission_denied?, unavailable?}` |
| POST | `/attendance/attempts/{id}/face` | Multipart optional `image` |
| POST | `/attendance/attempts/{id}/liveness` | Multipart optional `image` |
| POST | `/attendance/attempts/{id}/finalize` | Server decision and record |

### Location outcomes

`INSIDE_GEOFENCE`, `OUTSIDE_GEOFENCE`, `LOW_ACCURACY`, `PERMISSION_DENIED`, `UNAVAILABLE`, `STALE`.
`REVIEW_REQUIRED` is produced by the risk engine where policy allows review.

### Finalize response

```json
{
  "record_id": "uuid",
  "reference": "AX-20261109-AB12CD34",
  "session_id": "uuid",
  "status": "present",
  "classification": "FULL",
  "decision_source": "system",
  "decision": "ACCEPTED",
  "risk_score": 0,
  "reasons": [{ "code": "ALL_FACTORS_PASSED", "factor": "summary", "severity": "info", "message": "…" }],
  "check_in_at": "2026-11-09T04:02:11Z"
}
```

`REVIEW_REQUIRED` returns `status: review_required` and `classification: PENDING_REVIEW`; `REJECTED`
returns `status: rejected` and `classification: INVALID`.

## 7. Student read/review endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/student/dashboard` | Attendance percentage, active/upcoming sessions, subjects, recent records |
| GET | `/student/attendance?limit=` | Own history |
| GET | `/student/subjects` | Subject-wise sessions/present/percentage |
| GET | `/student/reviews` | Own review requests |
| POST | `/student/review-requests` | `{session_id, reason}` |
| GET | `/student/profile` | Own account and academic profile |
| GET | `/student/face-enrollment` | Enrollment status/metadata; never returns a template or image |
| POST | `/student/face-enrollment` | Multipart `image`, `consent=true`, `consent_version`; local provider only |
| DELETE | `/student/face-enrollment` | Clears the encrypted template and records deletion |

## 8. Reports

| Method | Path | Roles | Query |
|---|---|---|---|
| GET | `/reports/attendance` | admin, teacher | `class_id`, `subject_id`, `from`, `to` |
| GET | `/reports/export` | admin, teacher | same; returns `text/csv` attachment |

Teachers are restricted to their assigned classes; an unassigned `class_id` returns `403`.

Report rows: student, roll number, class, subject, sessions held, sessions present, attendance
percentage. A review-required record is not counted as present until resolved.

## 9. Health

| Method | Path | Description |
|---|---|---|
| GET | `/health/live` | Process liveness (no DB) |
| GET | `/health/ready` | Database check, provider names, environment, version |

## 10. Error codes used by the frontend

`NOT_AUTHENTICATED`, `FORBIDDEN`, `CSRF_FAILED`, `VALIDATION_ERROR`, `QR_INVALID`, `QR_EXPIRED`,
`QR_REVOKED`, `SESSION_NOT_OPEN`, `SESSION_EXPIRED`, `SESSION_CLOSED`, `ALREADY_RECORDED`,
`PIN_INVALID`, `PIN_UNAVAILABLE`, `VERIFICATION_PENDING`, `RATE_LIMITED`, `EMAIL_EXISTS`,
`ROLL_EXISTS`, `EMPLOYEE_EXISTS`, `WEAK_PASSWORD`, `IMPORT_CONFLICT`.

## 11. Contract limitations

- No API version negotiation beyond the `/v1` prefix.
- No pagination metadata beyond `limit`/`offset` on the audit/security/user lists.
- `GET /admin/users` returns role/profile data but never password hashes.
- OpenAPI documentation is enabled by default; a production deployment should restrict `/api/docs`
  at the ingress or disable it.
