import Link from "next/link";
import {
  AlertTriangle,
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Database,
  FileCheck2,
  Fingerprint,
  KeyRound,
  LockKeyhole,
  MapPin,
  Monitor,
  QrCode,
  ScanFace,
  ServerCog,
  ShieldAlert,
  ShieldCheck,
  Smartphone,
  UserCheck,
  Users,
} from "lucide-react";
import { BrandFooter, PublicHeader } from "@/components/shell";

const verificationFactors = [
  {
    icon: QrCode,
    title: "Dynamic session QR",
    body: "Cryptographically signed, session-bound and rotated on a configurable interval. Old tokens expire on their own schedule; rotating one student's screen never invalidates another student's scan.",
    status: "Implemented",
  },
  {
    icon: KeyRound,
    title: "Temporary PIN",
    body: "A per-session PIN generated with a secure random source, stored as an Argon2 hash, attempt-limited and invalidated when the session closes.",
    status: "Implemented",
  },
  {
    icon: MapPin,
    title: "Location evidence",
    body: "Browser geolocation is evaluated server-side with Haversine distance, accuracy thresholds and stale-timestamp checks. Missing permission is treated as evidence, not as cheating.",
    status: "Implemented",
  },
  {
    icon: ScanFace,
    title: "Face verification",
    body: "Genuine local OpenCV SFace matching against a consent-based, encrypted template — or an external provider. Unconfigured means UNAVAILABLE, never a fabricated match.",
    status: "Implemented (local)",
  },
  {
    icon: Fingerprint,
    title: "Liveness detection",
    body: "Optional local MiniFASNet single-frame anti-spoofing or an external provider. Spoof-like captures are FAILED; unavailable checks are recorded honestly. Not a challenge-response guarantee.",
    status: "Implemented (local)",
  },
  {
    icon: ShieldAlert,
    title: "Explainable risk engine",
    body: "Deterministic rules combine factor states into ACCEPTED, REJECTED or REVIEW_REQUIRED, with reason codes a teacher can inspect. It is not described as trained ML.",
    status: "Implemented",
  },
];

const implemented = [
  "Argon2id authentication with server-managed sessions",
  "Role-based access for administrator, teacher and student",
  "Academic configuration and CSV account provisioning",
  "Dynamic QR + PIN check-in with duplicate protection",
  "Server-side geofence evaluation",
  "Genuine local face matching with encrypted, consent-based templates",
  "Explainable risk decisions and teacher review queue",
  "Attendance reports and CSV export",
  "Audit and security event trails",
];

const pilotOnly = [
  "Local liveness is a single-frame anti-spoof check, not proof of a live person or a challenge-response guarantee",
  "Face/liveness accuracy and fairness require institutional evaluation; no claims are made here",
  "Local face templates require model installation, supervised enrollment and a DPIA",
  "BLUETOOTH presence monitoring is designed in the data model but not captured in this build",
  "Real biometric processing needs consent, a DPIA and legal review",
  "Institution data must be verified through authorized records, never seeded in production",
];

export default function LandingPage() {
  return (
    <div className="bg-white">
      <PublicHeader />

      {/* Hero */}
      <section className="relative overflow-hidden bg-white">
        <div className="absolute inset-x-0 top-0 h-[520px] bg-[radial-gradient(900px_420px_at_18%_0%,#EDF4FF_0%,rgba(237,244,255,0)_68%)]" aria-hidden />
        <div className="relative mx-auto grid max-w-7xl gap-12 px-4 pb-20 pt-14 sm:px-6 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pt-20">
          <div>
            <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#D4E3FF] bg-[#F5F9FF] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#1F55C7]">
              <ShieldCheck size={13} /> Attendance verification platform
            </p>
            <h1 className="max-w-2xl text-4xl font-semibold leading-[1.08] tracking-tight text-ink sm:text-5xl">
              Attendance that proves presence,
              <span className="text-brand"> not just a tap.</span>
            </h1>
            <p className="mt-5 max-w-xl text-base leading-relaxed text-[#475467]">
              AttendX AI is an intelligent attendance and anti-proxy verification system for
              educational institutions. It combines a rotating QR session, a temporary PIN,
              location evidence and configurable identity checks — then records an auditable,
              explainable decision.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-3">
              <Link
                href="/login"
                className="inline-flex h-12 items-center gap-2 rounded-xl bg-brand px-6 text-sm font-semibold text-white shadow-sm transition-colors hover:bg-brand-hover"
              >
                Sign in to the workspace <ArrowRight size={16} />
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex h-12 items-center rounded-xl border border-line bg-white px-5 text-sm font-semibold text-ink transition-colors hover:border-brand/40 hover:bg-active"
              >
                See the verification flow
              </a>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-xs text-muted">
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[#12855A]" /> No public role escalation
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[#12855A]" /> Server-side decisions
              </span>
              <span className="inline-flex items-center gap-1.5">
                <CheckCircle2 size={14} className="text-[#12855A]" /> Audit-first design
              </span>
            </div>
          </div>

          {/* Verification card mock */}
          <div className="relative mx-auto w-full max-w-md">
            <div className="absolute -right-6 -top-6 h-28 w-28 rounded-full bg-[#D4E3FF]/60 blur-2xl" aria-hidden />
            <div className="relative rounded-2xl border border-line bg-white p-5 shadow-[0_18px_50px_rgba(16,24,40,0.10)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">
                    Live attendance session
                  </p>
                  <p className="mt-1 text-sm font-semibold text-ink">TE Computer A · DBMS</p>
                </div>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-[#ECFDF3] px-2.5 py-1 text-[10px] font-bold text-[#067647]">
                  <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-[#12B76A]" /> OPEN
                </span>
              </div>

              <div className="mt-4 rounded-xl border border-line bg-[#FAFBFD] p-4">
                <div className="flex items-center gap-4">
                  <div className="grid h-24 w-24 shrink-0 grid-cols-6 gap-0.5 rounded-lg bg-white p-2 shadow-inner">
                    {Array.from({ length: 36 }).map((_, index) => (
                      <span
                        key={index}
                        className={
                          [0, 1, 4, 5, 2, 3, 6, 11, 12, 17, 18, 23, 24, 29, 30, 31, 34, 35, 8, 13, 26, 33].includes(index)
                            ? "rounded-[1px] bg-ink"
                            : "rounded-[1px] bg-transparent"
                        }
                      />
                    ))}
                  </div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                      Temporary PIN
                    </p>
                    <p className="mt-1 font-mono text-2xl font-bold tracking-[0.18em] text-ink">
                      7 4 2 9 1 6
                    </p>
                    <p className="mt-2 inline-flex items-center gap-1 text-[11px] text-muted">
                      <Clock3 size={12} /> Rotates in 00:24
                    </p>
                  </div>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                {[
                  ["Signed session QR", "pass", "Valid · bound to session"],
                  ["PIN verification", "pass", "Verified server-side"],
                  ["Classroom location", "review", "Review requested · low accuracy"],
                  ["Face provider", "na", "Not configured in this deployment"],
                ].map(([label, tone, detail]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between gap-3 rounded-lg border border-line px-3 py-2"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={
                          tone === "pass"
                            ? "flex h-5 w-5 items-center justify-center rounded-full bg-[#ECFDF3] text-[#067647]"
                            : tone === "review"
                              ? "flex h-5 w-5 items-center justify-center rounded-full bg-[#FFFAEB] text-[#B54708]"
                              : "flex h-5 w-5 items-center justify-center rounded-full bg-[#F2F4F8] text-muted"
                        }
                      >
                        {tone === "pass" ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                      </span>
                      <span className="text-xs font-medium text-ink">{label}</span>
                    </div>
                    <span className="text-right text-[10px] text-muted">{detail}</span>
                  </div>
                ))}
              </div>

              <div className="mt-4 flex items-center justify-between rounded-lg bg-[#F5F9FF] px-3 py-2.5">
                <span className="text-[11px] font-medium text-[#1F55C7]">
                  Decision: teacher review required
                </span>
                <span className="font-mono text-[10px] text-muted">risk 20</span>
              </div>
            </div>
            <p className="mt-3 text-center text-[10px] text-muted">
              Illustrative interface. Verification factor states are shown honestly, including
              unavailable providers.
            </p>
          </div>
        </div>
      </section>

      {/* Status strip */}
      <section className="border-y border-line bg-[#FAFBFD]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 py-4 text-xs sm:px-6">
          <p className="font-semibold text-ink">Build status, stated plainly:</p>
          <div className="flex flex-wrap gap-2">
            <span className="rounded-full border border-[#ABEFC6] bg-[#ECFDF3] px-2.5 py-1 font-semibold text-[#067647]">
              Core attendance flow implemented
            </span>
            <span className="rounded-full border border-[#ABEFC6] bg-[#ECFDF3] px-2.5 py-1 font-semibold text-[#067647]">
              Face + local liveness implemented
            </span>
            <span className="rounded-full border border-line bg-white px-2.5 py-1 font-semibold text-muted">
              BLE presence: future integration
            </span>
          </div>
        </div>
      </section>

      {/* Product overview */}
      <section id="product" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Product overview</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
              One attendance product. Two purpose-built experiences.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#475467]">
              AttendX AI focuses on attendance, verification, monitoring, reports and the
              administrative configuration those workflows need. It deliberately does not attempt to
              be a full college ERP.
            </p>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-line bg-white p-4">
                <Monitor size={18} className="text-brand" />
                <p className="mt-2 text-sm font-semibold text-ink">Desktop workspace</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  Administrators configure people and policy. Teachers run sessions and review
                  evidence on a full-screen live view.
                </p>
              </div>
              <div className="rounded-xl border border-line bg-white p-4">
                <Smartphone size={18} className="text-brand" />
                <p className="mt-2 text-sm font-semibold text-ink">Mobile student journey</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">
                  Scan with the native camera or the in-browser scanner, then complete each
                  verification step with clear permission explanations and recovery paths.
                </p>
              </div>
            </div>
          </div>
          <div className="rounded-2xl border border-line bg-[#FAFBFD] p-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Shared foundation</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {[
                [Database, "One PostgreSQL schema", "Classes, subjects, sessions, evidence, reviews and audit live in one transactional model."],
                [LockKeyhole, "One authentication system", "Argon2id, server sessions, HTTP-only cookies and CSRF protection for both interfaces."],
                [UserCheck, "One authorization model", "Resource-level checks: students see themselves; teachers see assigned sessions."],
                [BarChart3, "One source of truth", "Teacher live counts, student history and reports all read the same records."],
              ].map(([Icon, title, body]) => {
                const Component = Icon as typeof Database;
                return (
                  <div key={title as string} className="rounded-lg bg-white p-4">
                    <Component size={17} className="text-brand" />
                    <p className="mt-2 text-xs font-semibold text-ink">{title as string}</p>
                    <p className="mt-1 text-[11px] leading-relaxed text-muted">{body as string}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="bg-[#FAFBFD] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">The traditional problem</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
              A name on a sheet is not evidence of presence.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#475467]">
              Common attendance methods are convenient but leak trust: codes are shared, screenshots
              are forwarded, absent classmates are marked by friends, and records are hard to audit.
            </p>
          </div>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Shared QR screenshots", "A static code can be forwarded and reused outside the classroom."],
              ["Buddy marking", "One student submits attendance for an absent classmate."],
              ["Codes that never expire", "A code left on screen remains valid after the lecture."],
              ["No reliable audit", "Corrections happen without a decision trail or review history."],
            ].map(([title, body]) => (
              <div key={title} className="rounded-xl border border-line bg-white p-5">
                <ShieldAlert size={18} className="text-[#B42318]" />
                <p className="mt-3 text-sm font-semibold text-ink">{title}</p>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Solution */}
      <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">The AttendX approach</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
              Independent evidence layers, one accountable decision.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#475467]">
              No single factor is treated as proof. The backend evaluates each factor, records its
              state, and applies an explicit policy. Missing evidence can lead to review — it does
              not automatically label a student as dishonest.
            </p>
            <div className="mt-6 rounded-xl border border-[#D4E3FF] bg-[#F5F9FF] p-4 text-xs leading-relaxed text-[#1F3D7A]">
              <strong className="font-semibold">Honest boundary:</strong> AttendX AI reduces common
              proxy paths; it does not claim perfect prevention or perfect biometric accuracy.
              Determined collusion and sophisticated spoofing remain residual risks documented in the
              threat model.
            </div>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {verificationFactors.map((factor) => {
              const Icon = factor.icon;
              return (
                <div key={factor.title} className="rounded-xl border border-line bg-white p-5">
                  <div className="flex items-start justify-between gap-2">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-active text-brand">
                      <Icon size={18} />
                    </span>
                    <span
                      className={
                        factor.status.startsWith("Implemented")
                          ? "rounded-full bg-[#ECFDF3] px-2 py-0.5 text-[10px] font-bold text-[#067647]"
                          : "rounded-full bg-[#FFFAEB] px-2 py-0.5 text-[10px] font-bold text-[#B54708]"
                      }
                    >
                      {factor.status}
                    </span>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-ink">{factor.title}</p>
                  <p className="mt-1.5 text-xs leading-relaxed text-muted">{factor.body}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="scroll-mt-24 bg-[#0D1B3A] py-20 text-white">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#9DBAFF]">How it works</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight">
              The teacher opens a session. The student proves the check-in.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#C9DAFF]">
              Every step is validated by the backend. A QR code never marks attendance by itself,
              and a frontend timer is not what closes a session.
            </p>
          </div>
          <div className="mt-10 grid gap-8 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/12 bg-white/[0.04] p-6">
              <div className="flex items-center gap-2 text-[#9DBAFF]">
                <ClipboardCheck size={16} />
                <span className="text-xs font-bold uppercase tracking-[0.12em]">Teacher</span>
              </div>
              <ol className="mt-5 space-y-4">
                {[
                  ["Select an assigned class, subject and classroom", "The backend rejects a session outside the teacher's assignment."],
                  ["Configure the window and verification factors", "Window and QR refresh are independent values."],
                  ["Start the session", "The server opens the session, generates the PIN and first signed QR."],
                  ["Monitor the live view", "Counts, factor states and review flags update from the database."],
                  ["Review and correct", "Flagged attempts are resolved with a recorded reason and correction history."],
                ].map(([title, body], index) => (
                  <li key={title} className="flex gap-3">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-[11px] font-bold text-[#9DBAFF]">
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{title}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-[#C9DAFF]">{body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
            <div className="rounded-2xl border border-white/12 bg-white/[0.04] p-6">
              <div className="flex items-center gap-2 text-[#9DBAFF]">
                <Smartphone size={16} />
                <span className="text-xs font-bold uppercase tracking-[0.12em]">Student</span>
              </div>
              <ol className="mt-5 space-y-4">
                {[
                  ["Scan the classroom QR", "Native camera or in-browser scanner; the token is validated server-side."],
                  ["Enter the temporary PIN", "Attempts are limited and security events are recorded without logging the PIN."],
                  ["Share location evidence", "The browser explains why location is requested before the prompt."],
                  ["Complete required identity checks", "If a provider is unavailable, the result is UNAVAILABLE — never a fake pass."],
                  ["See the confirmed result", "Accepted, review-required, rejected or expired, with a reference for accepted attendance."],
                ].map(([title, body], index) => (
                  <li key={title} className="flex gap-3">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/10 text-[11px] font-bold text-[#9DBAFF]">
                      {index + 1}
                    </span>
                    <div>
                      <p className="text-sm font-semibold">{title}</p>
                      <p className="mt-0.5 text-xs leading-relaxed text-[#C9DAFF]">{body}</p>
                    </div>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      </section>

      {/* Interfaces */}
      <section id="interfaces" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-20 sm:px-6">
        <div className="grid gap-10 lg:grid-cols-2">
          <div className="rounded-2xl border border-line bg-[#FAFBFD] p-6">
            <div className="flex items-center gap-2">
              <Monitor size={18} className="text-brand" />
              <h3 className="text-lg font-semibold text-ink">Desktop web</h3>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#475467]">
              Built for administrators and teachers: account provisioning, academic configuration,
              policy management, a full-screen live session with QR and PIN, review queue, reports,
              audit and security visibility.
            </p>
            <ul className="mt-4 space-y-2 text-xs text-muted">
              {["White sidebar and clear information hierarchy", "Live counts sourced from real queries", "Review and correction trails", "Exportable attendance reports"].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-[#12855A]" /> {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-line bg-[#FAFBFD] p-6">
            <div className="flex items-center gap-2">
              <Smartphone size={18} className="text-brand" />
              <h3 className="text-lg font-semibold text-ink">Mobile student web</h3>
            </div>
            <p className="mt-2 text-sm leading-relaxed text-[#475467]">
              Built mobile-first, not a resized dashboard: large touch targets, bottom navigation,
              explicit permission explanations, camera recovery paths and a clear result screen.
            </p>
            <ul className="mt-4 space-y-2 text-xs text-muted">
              {["Native camera QR entry and in-browser scanning", "Step-by-step verification progress", "Attendance history and subject summaries", "Review requests for disputed cases"].map((item) => (
                <li key={item} className="flex items-center gap-2">
                  <CheckCircle2 size={13} className="text-[#12855A]" /> {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Security */}
      <section id="security" className="scroll-mt-24 bg-[#FAFBFD] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="grid gap-12 lg:grid-cols-[0.9fr_1.1fr]">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Security architecture</p>
              <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
                Decisions are server-side. Access is scoped to the person.
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-[#475467]">
                AttendX does not store long-lived auth tokens in local storage. It does not expose
                biometric evidence to administrators by default, and it records security-relevant
                actions without logging secrets.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              {[
                [LockKeyhole, "Argon2id passwords", "Unique hashes, account lockout and generic failure messages."],
                [KeyRound, "Server-managed sessions", "Opaque token hashed at rest, HTTP-only and SameSite cookies."],
                [ShieldAlert, "CSRF and origin checks", "Mutating requests require a session-bound CSRF header."],
                [UserCheck, "Least privilege", "Resource-level checks for every teacher and student action."],
                [FileCheck2, "Immutable audit trail", "Provisioning, sessions, reviews and exports are recorded."],
                [ServerCog, "Operational honesty", "Provider health is visible; unavailable is a first-class state."],
              ].map(([Icon, title, body]) => {
                const Component = Icon as typeof ShieldCheck;
                return (
                  <div key={title as string} className="rounded-xl border border-line bg-white p-5">
                    <Component size={18} className="text-brand" />
                    <p className="mt-3 text-sm font-semibold text-ink">{title as string}</p>
                    <p className="mt-1 text-xs leading-relaxed text-muted">{body as string}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Privacy */}
      <section id="privacy" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-20 sm:px-6">
        <div className="grid gap-12 lg:grid-cols-[0.85fr_1.15fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Privacy by design</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
              Collect the minimum needed for a defensible decision.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#475467]">
              Attendance verification touches personal data. The build keeps location evidence
              scoped to the check-in moment, stores verification metadata rather than raw face
              images, and exposes evidence only to authorized staff handling a review.
            </p>
          </div>
          <div className="space-y-3">
            {[
              ["No continuous tracking", "Location is requested for the check-in, not as an ongoing background feed."],
              ["No raw biometric images in the core record", "The evidence model stores provider outcomes, scores and model version — not a face gallery."],
              ["Explicit biometric consent fields", "Enrollment metadata records consent version and deletion state."],
              ["Retention and deletion are configuration concerns", "The schema supports deletion workflows; institutional policy must set the actual periods."],
              ["Indian DPDP context", "Real biometric processing requires institutional authorization, consent and legal review before a pilot."],
            ].map(([title, body]) => (
              <div key={title} className="rounded-xl border border-line bg-white p-4">
                <p className="text-sm font-semibold text-ink">{title}</p>
                <p className="mt-1 text-xs leading-relaxed text-muted">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Technology */}
      <section id="technology" className="scroll-mt-24 bg-[#FAFBFD] py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-brand">Technology</p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-ink">
              A modular monolith that can be operated by a small team.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-[#475467]">
              Next.js and FastAPI share one PostgreSQL schema. Docker Compose defines the runtime.
              Face verification can run locally with OpenCV SFace and encrypted templates, while
              liveness and externally approved identity services remain explicit provider contracts.
            </p>
          </div>
          <div className="mt-8 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["Frontend", "Next.js App Router · React · TypeScript · Tailwind CSS"],
              ["Backend", "Python · FastAPI · Pydantic · SQLAlchemy 2 · Alembic"],
              ["Data", "PostgreSQL in production · SQLite for local test profile"],
              ["Verification", "Signed QR · Argon2 PIN · Haversine geofence · provider adapters"],
            ].map(([title, body]) => (
              <div key={title} className="rounded-xl border border-line bg-white p-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-brand">{title}</p>
                <p className="mt-2 text-xs leading-relaxed text-muted">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits + limitations */}
      <section id="limitations" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-20 sm:px-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-[#ABEFC6] bg-[#F3FCF7] p-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-[#067647]">Implemented in this build</p>
            <h3 className="mt-2 text-xl font-semibold text-ink">What you can evaluate today</h3>
            <ul className="mt-4 space-y-2.5">
              {implemented.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-[#05603A]">
                  <CheckCircle2 size={15} className="mt-0.5 shrink-0" /> {item}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-[#FEDF89] bg-[#FFFCF2] p-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-[#B54708]">Pilot dependencies and limits</p>
            <h3 className="mt-2 text-xl font-semibold text-ink">What must be established first</h3>
            <ul className="mt-4 space-y-2.5">
              {pilotOnly.map((item) => (
                <li key={item} className="flex items-start gap-2 text-sm text-[#7A3D06]">
                  <AlertTriangle size={15} className="mt-0.5 shrink-0" /> {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Demo request */}
      <section className="bg-brand py-16">
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-6 px-4 sm:px-6 lg:flex-row lg:items-center">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#BFD3FF]">Institutional pilot</p>
            <h2 className="mt-2 text-3xl font-semibold tracking-tight text-white">
              Evaluate AttendX AI with your own authorized data.
            </h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[#D7E4FF]">
              A pilot starts with a named institutional sponsor, an approved data-flow review and a
              configured verification provider. We do not claim a live campus deployment.
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
            <a
              href="mailto:pilot@attendx.example?subject=AttendX%20AI%20pilot%20request"
              className="inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-white px-5 text-sm font-semibold text-brand hover:bg-[#EDF4FF]"
            >
              Request a pilot <ArrowRight size={16} />
            </a>
            <Link
              href="/login"
              className="inline-flex h-12 items-center justify-center rounded-xl border border-white/30 px-5 text-sm font-semibold text-white hover:bg-white/10"
            >
              Authorized sign in
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-line bg-[#FAFBFD] px-6 py-5">
          <div className="flex items-center gap-3">
            <Users size={19} className="text-brand" />
            <p className="text-sm text-ink">
              <strong className="font-semibold">For ZEAL College of Engineering &amp; Research, Pune</strong>{" "}
              — this build is a pilot-ready technical foundation, not an authoritative student record
              system.
            </p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-white px-3 py-1 text-[10px] font-semibold text-muted">
            <ClipboardCheck size={12} /> Independent project
          </span>
        </div>
      </section>

      <BrandFooter />
    </div>
  );
}
