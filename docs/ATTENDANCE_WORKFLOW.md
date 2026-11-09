# Attendance Workflow — AttendX AI

## 1. Lifecycle overview

```text
Teacher: create (scheduled) → open (PIN + first QR) → monitor → close
Student: scan → validate → check-in attempt → PIN → location → [face] → [liveness]
         → finalize → risk decision → record (+ review request when needed)
```

The backend owns every state transition. Frontend timers and counters are display-only.

## 2. Session states

| State | Meaning | Allowed next |
|---|---|---|
| `scheduled` | Created, QR/PIN not yet issued | `open`, `cancelled` |
| `open` | Check-in window active; QR tokens and PIN valid | `closed`, `expired` |
| `closed` | Teacher closed; tokens revoked, PIN cleared | terminal |
| `expired` | Window elapsed and detected on access/finalization | terminal |
| `cancelled` | Reserved for future use; not exposed in UI | terminal |

Opening a session sets the window from the moment of opening (`now + window_seconds`) so a late start
still gives students the configured check-in period. It cannot be opened more than ten minutes before
the planned start, and not after the planned window has elapsed. Closing revokes all active QR tokens,
clears the PIN hash and marks in-progress attempts `abandoned`.

## 3. QR token design

- Payload: `{ "sid": session_uuid, "nonce": random, "iat": unix, "exp": unix }`.
- Format: `v1.<base64url(payload)>.<base64url(HMAC-SHA256(payload_b64))>`.
- Signing key: `QR_SIGNING_KEY` (falls back to `SECRET_KEY` if unset; production should set both).
- `qr_tokens` stores the nonce, session, issue/expiry and revocation, **not** the token string.
- Expiry = now + refresh interval + grace; also capped at session end + grace.
- Rotation creates a new token but leaves earlier tokens valid until their own expiry. A student who
  already started an attempt is unaffected. Server-side revocation happens on close.
- The token URL is `WEB_ORIGIN/attend/<token>`; the frontend sends the token to the API. The token
  alone grants no attendance.

Validation checks, in order: signature → nonce/token row → row expiry → session open → window not
elapsed. A closed session invalidates every token.

## 4. PIN

- Generated with `secrets.randbelow` per digit (no modulo bias), default length 6.
- Stored as an Argon2id hash; never logged, never returned except at generation/regeneration to the
  authenticated teacher.
- Attempts are counted on the attempt and additionally rate-limited. On the fifth failure the attempt
  is rejected and a rejected attendance record is created, which blocks a fresh brute-force attempt
  for the same session.
- Cleared on session close; expired with the session window.

## 5. Location evidence

Request fields: latitude, longitude, accuracy, optional client timestamp, or explicit
`permission_denied` / `unavailable`.

Evaluation order:

1. Permission denied → `PERMISSION_DENIED`.
2. Missing/unavailable coordinates → `UNAVAILABLE`.
3. Invalid ranges → `UNAVAILABLE`.
4. Client timestamp is not provided → no staleness check; otherwise absolute skew > 120 s →
   `STALE`.
5. No/invalid accuracy → `LOW_ACCURACY`.
6. Accuracy worse than the geofence maximum → `LOW_ACCURACY`.
7. Haversine distance > radius → `OUTSIDE_GEOFENCE`.
8. Otherwise → `INSIDE_GEOFENCE`.

The raw coordinates are kept only as attempt evidence for review. The product does not continuously
track students. Browser GPS is not tamper-proof; it is evidence, not proof of classroom presence.

## 6. Face and liveness

Both are **separate** provider contracts:

- Face verification requires an authorized `biometric_enrollments` row with consent and an active
  status. The optional local OpenCV provider matches a YuNet+SFace 128-D embedding against the
  decrypted enrolled template (cosine threshold 0.363). If no provider is configured, the student
  has no image/enrollment, or the capture is unusable, the result is `UNAVAILABLE` with a precise
  reason code. A detected face below threshold is `FAILED` (`FACE_MISMATCH`).
- Liveness calls its own provider; simple blink/head-turn prompts are not claimed as replay-proof.
  No liveness provider is configured by default.
- The HTTP adapter sends one image and expects
  `{status: PASSED|FAILED, score?: 0..1, reason_code?, provider?, model_version?}`. Network failures
  become `UNAVAILABLE`, malformed responses become `UNAVAILABLE`, and no score is invented.
- Images are not persisted by AttendX; only status, optional score, provider, model version and small
  metadata are stored as evidence.

## 7. Explainable risk engine

Inputs: QR state, PIN state, GPS state, face state, liveness state, required-factor snapshot,
outside-geofence review policy, duplicate attempt flag, PIN-attempt flag.

Rules (all deterministic, all explained by reason codes):

| Condition | Outcome |
|---|---|
| Duplicate official record | `REJECTED` — `DUPLICATE_ATTENDANCE` |
| QR failed | `REJECTED` — `QR_INVALID` |
| PIN failed / attempts exceeded | `REJECTED` |
| Face failed | `REJECTED` — `FACE_MISMATCH` |
| Liveness failed | `REJECTED` — `LIVENESS_FAILED` |
| Outside geofence, review allowed | `REVIEW_REQUIRED` — `GPS_OUTSIDE_GEOFENCE_REVIEW` |
| Outside geofence, review disabled | `REJECTED` |
| Low accuracy / unavailable / permission denied / stale (required) | `REVIEW_REQUIRED` |
| Face or liveness unavailable (required) | `REVIEW_REQUIRED` |
| Required factor still pending | `REVIEW_REQUIRED`; the flow also blocks finalization earlier |
| All required factors passed | `ACCEPTED` |

Risk score is a **points total** (20 per review reason, 45 per block, capped at 100), not a
probability. The engine is a rule engine, not trained ML.

## 8. Finalization and records

Finalization requires the attempt to be in progress, the session open, the 30-second processing grace
not exceeded, and every required factor submitted. It:

1. Evaluates risk.
2. Creates exactly one `attendance_records` row with a unique reference.
3. Updates the attempt status/risk fields.
4. Opens an automatic `review_requests` row when the outcome is `REVIEW_REQUIRED`.
5. Audits/security-logs rejected outcomes.
6. Returns decision, status, classification, reasons and the reference.

Status mapping: accepted → `present` / `FULL`; review → `review_required` / `PENDING_REVIEW`;
rejected → `rejected` / `INVALID`. Duplicate finalization returns the existing result idempotently or
a `409 ALREADY_RECORDED` at check-in.

## 9. Teacher review and correction

- Reviews are scoped to the teacher's own sessions.
- The teacher chooses approved/rejected and writes a required note; an approved review marks
  attendance present and a rejected review marks it absent.
- Every change writes an `attendance_corrections` row with old/new status and classification and an
  audit event. The original record and decision source remain traceable.

## 10. Presence monitoring (designed, not captured)

Initial check-in is not the same as remaining for the whole lecture. The schema includes
`presence_events` and the policy includes `presence_monitoring_enabled` plus full/partial ratios. The
intended design:

- A classroom-supported proximity mechanism (e.g. BLE beacon) emits presence/loss events.
- Presence ratio over the lecture decides `FULL` / `PARTIAL` / `INTERRUPTED`.
- Final classification is policy-based and auditable; `INVALID`/`ABSENT` require evidence or teacher
  decision.
- Browser BLE support is not universal and is not implemented in this build. Do not claim it.

## 11. Edge cases

| Case | Behaviour |
|---|---|
| Student scans twice rapidly | Second start returns the existing active attempt or `ALREADY_RECORDED` after finalization |
| QR rotates during a student's flow | Attempt is already bound; later steps do not re-check the old token |
| Teacher closes while a student is mid-flow | Finalization returns `SESSION_CLOSED`; the attempt is abandoned and reviewable |
| GPS permission denied | Recorded, likely review — not automatic cheating |
| Provider outage | `UNAVAILABLE`, review if mandatory |
| Device clock skew | `STALE` when the client timestamp differs from server time beyond threshold |
| Student not enrolled | `403` before an attempt is created |
| Session opened very late | Window starts at open; opening after planned end is rejected |
| Duplicate finalize request | Unique constraint + idempotent response |
