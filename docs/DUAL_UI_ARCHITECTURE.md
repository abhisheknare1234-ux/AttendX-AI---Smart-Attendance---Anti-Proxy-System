# Dual UI Architecture — Desktop and Mobile

## 1. Why two experiences

Administrators and teachers need dense configuration, tables, reports and a large QR display.
Students need a fast, thumbs-first check-in in a classroom, often on a mid-range phone with one hand
and intermittent connectivity. Resizing the desktop dashboard would fail both needs, so the product
has two purpose-built layouts sharing one backend, one database and one authorization model.

## 2. Route map

### Public
| Route | Purpose |
|---|---|
| `/` | Landing page: problem, solution, verification factors, security/privacy, limits, pilot CTA |
| `/login` | Split-screen sign-in; role-based redirect; safe `next` parameter |

### Administrator (desktop)
`/admin` overview · `/admin/users` (accounts + CSV import) · `/admin/students` · `/admin/teachers` ·
`/admin/classes` · `/admin/subjects` · `/admin/enrollments` · `/admin/assignments` ·
`/admin/classrooms` · `/admin/geofences` · `/admin/policies` · `/admin/verification` ·
`/admin/reports` · `/admin/audit` · `/admin/security` · `/admin/health` · `/admin/settings`

### Teacher (desktop)
`/teacher` overview · `/teacher/classes` · `/teacher/subjects` · `/teacher/students` ·
`/teacher/sessions/new` · `/teacher/sessions` · `/teacher/sessions/{id}` live ·
`/teacher/reviews` · `/teacher/reports` · `/teacher/profile`

### Student (mobile-first)
`/student` home · `/student/scan` · `/student/attendance` history · `/student/subjects` ·
`/student/reviews` · `/student/profile` · `/attend/{token}` — QR entry and verification flow

### Account
`/account/password` — available to all authenticated roles.

## 3. Shared shell and guard strategy

- `AuthProvider` fetches `/auth/me` on load and exposes user, loading, login, logout and refresh.
- `RequireRole` redirects unauthenticated users to `/login?next=<path>` and renders a clear
  role-mismatch screen instead of leaking another role's UI.
- `DashboardShell` renders the white sidebar, mobile drawer, top bar and forced-password banner for
  admin/teacher.
- `StudentShell` renders the mobile header, bottom navigation and safe-area padding. The layout stays
  narrow on desktop rather than becoming a dashboard.

## 4. Two QR entry methods

1. **Native phone camera:** the QR encodes an HTTPS URL on the configured web origin
   (`WEB_ORIGIN/attend/<signed-token>`). The phone camera opens that URL, which runs the same
   backend-validated flow.
2. **In-browser scanner:** `jsQR` reads frames from `getUserMedia` on a canvas. Frames are processed
   locally and are never uploaded. The scanner is started by an explicit user action and cleaned up
   on unmount.

Both paths converge on `POST /attendance/qr/validate` and `POST /attendance/check-ins`. The QR never
marks attendance by itself.

### Token safety

- Only the signed token is accepted; arbitrary URLs are rejected.
- The scanner accepts either a full URL whose path matches `/attend/<token>` or a raw `v1.*` token.
- The token is signed by the API and expiry-checked server-side; tampering returns `QR_INVALID`.

### Camera and location recovery

- Camera unsupported → explain and direct the student to the native camera path.
- Permission denied → specific guidance, plus a manual link paste option.
- No camera found → direct to native camera.
- Location denied/unavailable → the student can submit that fact as evidence; risk policy may route
  to teacher review rather than reject.

## 5. Teacher live session screen

- Full-width QR, PIN card (displayed only when generated/regenerated), copyable session link.
- Countdown to session close and to QR rotation, driven by server timestamps.
- Stat cards: eligible, accepted, pending, review required, rejected, seconds left.
- Recent attempts table with factor statuses and risk decisions.
- Open/close/regenerate actions hit the backend; the page polls every 2 seconds while open.
- Closing requires confirmation and explains that tokens are revoked and in-progress attempts are
  abandoned.

## 6. Responsive behaviour

- Desktop tables scroll horizontally on narrow viewports; low-priority columns hide below breakpoints.
- Modals become bottom sheets on phones.
- Typography and touch targets remain usable at 320 px width.
- The student flow never relies on hover and never presents desktop-sized tables.

## 7. Shared contracts

Both interfaces use the same typed API client (`apps/web/lib/api.ts`), cookies and CSRF header. There
is no second authentication mechanism, no separate database and no mock data in the UI. Role-specific
routes call the same endpoints the tests exercise.
