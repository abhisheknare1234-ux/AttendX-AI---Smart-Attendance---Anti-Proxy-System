# Reference Project Analysis — SnapClass

**Analysed repositories**

- Application: <https://github.com/shradha-khapra/ai-attendance-project-app> (public, default branch `main`, inspected 2026-11-09)
- Landing page: <https://github.com/shradha-khapra/ai-attendance-project-landing> (public, default branch `main`)

Both repositories contain no licence file (`license: null` in the GitHub API metadata). They are
therefore **all rights reserved** by default. AttendX AI uses them as conceptual references only and
copies no code, assets, fonts, copy or credentials from them.

## 1. What SnapClass implements

**App (Python, 16 KB repository, ~30 files):**

- Streamlit single-page application (`app.py`) with three screens: home, teacher, student. Screen
  selection is held in `st.session_state`; role state is a plain session string.
- Data layer: Supabase (hosted PostgreSQL) accessed with the `supabase` Python client
  (`src/database/db.py`) using a URL and key from `st.secrets`. Tables referenced: `teachers`,
  `students`, `subjects`, `subject_students`, `attendance_logs`.
- Authentication: teacher self-registration with username + password; `bcrypt` hashing; login is a
  direct table lookup. Students are created by a teacher with a name plus face/voice embeddings;
  students log in to a "student" view through the same app session, with no independently
  authenticated student account.
- Face recognition: `dlib` + `face_recognition_models` produce 128-D embeddings; an SVM
  (`SVC(kernel="linear", probability=True)`) is trained over all enrolled students; attendance is
  inferred by scanning one or more **classroom photos uploaded by the teacher**, then matching each
  detected face to a student at an L2 threshold of 0.6.
- Voice biometrics: `resemblyzer` embeddings over teacher-recorded bulk audio, with silence splitting
  via `librosa`; cosine similarity threshold 0.65.
- Attendance records: writes `attendance_logs` rows (`student_id`, `subject_id`, timestamp,
  `is_present`) per uploaded photo batch.
- Subjects are joined with a share code / QR-like link (`join-code` query parameter) that enrolls a
  student into a subject.
- Landing page: small Flask app serving a static marketing page plus a few screenshots and a custom
  font; deploy target Vercel.

## 2. What AttendX AI can learn from it

- **Instant teacher feedback matters.** The reference's best product idea is the immediate
  present/absent table after capture. AttendX keeps a live session view with per-student evidence
  status rather than a batch after-the-fact result.
- **Low-friction enrolment.** Student provisioning should be simple for the institution. AttendX uses
  administrator-provisioned accounts plus CSV import, and an explicit consent/enrolment step for any
  biometric factor.
- **Teacher-controlled session lifecycle** is the right mental model. AttendX makes it stricter:
  server-authoritative open/close/expiry, plus auditable state transitions.
- **Subject join codes** are convenient; AttendX replaces them with per-session, short-lived,
  rotating QR tokens bound to a session and a teacher authorisation check.
- **Reference dashboards are useful inspiration for information hierarchy** (subject cards, counts,
  records table), but AttendX's design language and component architecture are independently built.

## 3. Architectural differences

| Concern | SnapClass | AttendX AI |
|---|---|---|
| Application shape | Streamlit monolith, hosted UI | FastAPI backend + Next.js dual web UI |
| Database | Supabase (hosted Postgres) with service-role key | SQLAlchemy 2 + PostgreSQL (SQLite dev profile), Alembic migrations |
| Auth | In-app session state, bcrypt, public teacher sign-up | Server-side sessions, Argon2id, HTTP-only cookies, CSRF, RBAC, admin-only provisioning |
| Attendance trigger | Teacher photo capture / voice recording | Student scans rotating QR, enters PIN, submits location, face/liveness evidence; backend decides |
| Identity proof | 128-D face embedding comparison at capture time | Layered factor evidence with explicit `PASSED/FAILED/UNAVAILABLE/NOT_REQUIRED/PENDING_REVIEW` states |
| Anti-proxy | Not the focus; class photos are proxy-resistant only incidentally | QR rotation + PIN + geofence + face + liveness + duplicate/replay detection + explainable risk |
| Audit | None visible | Immutable audit/security event tables, review and correction history |
| Presence over lecture | Not addressed | Optional presence-event model and policy-driven final classification (schema implemented; BLE capture is a documented future integration) |
| Deployment | Streamlit Cloud / hosted Supabase | Docker Compose (API, web, Postgres) + migration/health checks |

## 4. Features AttendX AI needs that the reference does not establish

1. Session model with independent attendance window and QR refresh interval.
2. Cryptographically signed, rotating QR tokens with server-side replay binding.
3. Temporary PIN with attempt limits, rate limiting and secure storage.
4. Browser geolocation evidence with Haversine distance and explicit quality states.
5. Genuine, provider-abstracted face verification and liveness with honest `UNAVAILABLE` states
   when no provider is configured. (The reference's face matching is real, but it is teacher-captured
   bulk recognition, not a student-authenticated verification step.)
6. Explainable risk engine with reason codes and review workflow.
7. Administrator role, least-privilege authorization, audit trail, security monitoring.
8. Mobile-first student experience with native-camera and in-browser QR entry paths.
9. Reports, CSV import/export, data-retention controls.
10. Operational health checks, migrations, tests, deployment configuration.

## 5. Potential security concerns observed in the reference

- **Teacher self-registration** means anyone who can reach the app can create a teacher account and
  a subject. AttendX restricts account creation to administrators.
- **Supabase service-role key** in `st.secrets` bypasses row-level security; any compromised app
  process or secret leak exposes the whole database. A least-privilege key or a backend-owned DB is
  required.
- **No server-side session management**: Streamlit session state is per-browser-session and not a
  revocable authentication session; logout handling is only client-side state deletion.
- **Biometric templates in the database** with no consent, retention or deletion workflow visible.
- **Bulk photo capture** of a classroom creates a surveillance surface and may capture non-enrolled
  people; there is no operator consent or data-minimisation design.
- **No rate limiting, CSRF strategy, audit trail, or account lockout** visible in the code.
- **Attendance writes grouped only by a client-supplied timestamp**; no uniqueness constraint against
  duplicate submissions.
- **Thresholds hard-coded** (0.6 L2, 0.65 cosine) with no evaluation, calibration, provider/version
  metadata, or liveness check.

These are observations from public code, not a penetration test of the live demo.

## 6. Reusable engineering concepts

- Immediate per-student result display after verification.
- Embedding-based face matching with a distance threshold as a baseline approach.
- Voice/face embeddings as optional auxiliary signals.
- Subject sharing via QR/deep link to reduce enrolment friction.
- Clear teacher/student screen separation.

These concepts are reimplemented independently in AttendX's own architecture; no source code is
reused.

## 7. Licensing and reuse restrictions

- GitHub metadata reports **no licence** for either repository. Under default copyright, no copying,
  modification or redistribution rights are granted. This project therefore treats the references as
  **read-only research material**.
- No code, CSS, fonts, images, screenshots, model files, dataset or credential from the references is
  included in AttendX AI.
- Third-party libraries used by AttendX AI are listed with their licences in
  `docs/THIRD_PARTY_NOTICES.md`; the face/liveness provider contract is defined by AttendX AI itself.

## 8. Limitations of this analysis

- Repository inspection used the public GitHub API and raw file endpoints; the live application,
  Supabase schema, secrets, deployment configuration and runtime behaviour were **not** accessed.
- The analysis covers the files present at the inspected commit (repository metadata updated
  2026-11-05, code pushed 2026-04-18) and may not reflect later changes.
