"use client";

import Link from "next/link";
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Clock3,
  ListChecks,
  QrCode,
  ScanLine,
  ShieldCheck,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Skeleton,
  statusTone,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime, titleCase } from "@/lib/api";
import type { StudentDashboard } from "@/lib/types";

export default function StudentHomePage() {
  const { user } = useAuth();
  const dashboard = useApiData<StudentDashboard>("/student/dashboard");
  const data = dashboard.data;

  return (
    <div>
      <PageHeader
        eyebrow="Student"
        title={`Hello, ${user?.full_name?.split(" ")[0] ?? "student"}`}
        description={data ? `${data.roll_number} · verified attendance overview` : "Your verified attendance overview"}
      />

      {dashboard.error ? (
        <div className="mb-4">
          <Alert tone="danger" title="Could not load your dashboard">
            {dashboard.error}
          </Alert>
        </div>
      ) : null}

      {dashboard.loading ? (
        <div className="space-y-4">
          <Skeleton className="h-40" />
          <Skeleton className="h-24" />
          <Skeleton className="h-48" />
        </div>
      ) : data ? (
        <>
          <Card className="overflow-hidden">
            <div className="bg-brand p-6 text-white">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#BFD3FF]">
                    Your attendance
                  </p>
                  <p className="mt-1 text-5xl font-semibold tracking-tight">
                    {data.attendance_percentage === null ? "—" : `${data.attendance_percentage}%`}
                  </p>
                  <p className="mt-1 text-xs text-[#D7E4FF]">
                    {data.attended_sessions} of {data.total_sessions} held sessions recorded present
                  </p>
                </div>
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/15">
                  <ShieldCheck size={24} />
                </span>
              </div>
              <Link
                href="/student/scan"
                className="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-white text-sm font-bold text-brand hover:bg-[#EDF4FF]"
              >
                <ScanLine size={18} /> Scan attendance QR
              </Link>
            </div>
            <div className="grid grid-cols-3 divide-x divide-line">
              <div className="p-3 text-center">
                <p className="text-lg font-semibold text-ink">{data.total_sessions}</p>
                <p className="text-[10px] text-muted">Held sessions</p>
              </div>
              <div className="p-3 text-center">
                <p className="text-lg font-semibold text-ink">{data.attended_sessions}</p>
                <p className="text-[10px] text-muted">Present</p>
              </div>
              <div className="p-3 text-center">
                <p className="text-lg font-semibold text-ink">{data.pending_reviews}</p>
                <p className="text-[10px] text-muted">Pending reviews</p>
              </div>
            </div>
          </Card>

          {data.active_sessions.length ? (
            <Card className="mt-4 border-[#ABEFC6]">
              <CardHeader
                title="Session open now"
                description="Scan the QR on your teacher's screen to check in."
                action={<Badge tone="green">Open</Badge>}
              />
              <ul className="divide-y divide-line">
                {data.active_sessions.map((session) => (
                  <li key={session.session_id} className="flex items-center justify-between gap-3 px-4 py-3">
                    <div>
                      <p className="text-sm font-semibold text-ink">{session.subject_name}</p>
                      <p className="text-[11px] text-muted">
                        {session.class_name} · closes in {Math.max(1, Math.round(session.seconds_remaining / 60))} min
                      </p>
                    </div>
                    <Link href="/student/scan">
                      <Button size="sm">
                        <QrCode size={14} /> Scan
                      </Button>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          {data.upcoming_sessions.length ? (
            <Card className="mt-4">
              <CardHeader title="Upcoming sessions" description="Scheduled by your teachers." />
              <ul className="divide-y divide-line">
                {data.upcoming_sessions.map((session) => (
                  <li key={session.session_id} className="flex items-center justify-between gap-3 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-ink">{session.subject_name}</p>
                      <p className="text-[11px] text-muted">{session.class_name}</p>
                    </div>
                    <span className="text-right text-[11px] text-muted">
                      {formatDateTime(session.ends_at)}
                    </span>
                  </li>
                ))}
              </ul>
            </Card>
          ) : null}

          <div className="mt-4 grid grid-cols-2 gap-3">
            <Link
              href="/student/attendance"
              className="rounded-xl border border-line bg-white p-4 transition-colors hover:border-brand/40 hover:bg-active"
            >
              <CalendarClock size={18} className="text-brand" />
              <p className="mt-2 text-sm font-semibold text-ink">Attendance history</p>
              <p className="mt-0.5 text-[11px] text-muted">Every recorded decision and reference.</p>
            </Link>
            <Link
              href="/student/reviews"
              className="rounded-xl border border-line bg-white p-4 transition-colors hover:border-brand/40 hover:bg-active"
            >
              <ListChecks size={18} className="text-brand" />
              <p className="mt-2 text-sm font-semibold text-ink">Review requests</p>
              <p className="mt-0.5 text-[11px] text-muted">Ask a teacher to review disputed attendance.</p>
            </Link>
          </div>

          <Card className="mt-4">
            <CardHeader
              title="Subject attendance"
              description="Held sessions and present records by subject."
              action={
                <Link href="/student/subjects" className="text-xs font-semibold text-brand hover:underline">
                  All subjects
                </Link>
              }
            />
            {!data.subjects.length ? (
              <EmptyState
                icon={<ListChecks size={20} />}
                title="No subject enrolments"
                description="Your administrator has not enrolled you in a class yet."
              />
            ) : (
              <ul className="divide-y divide-line">
                {data.subjects.slice(0, 4).map((subject) => (
                  <li key={subject.subject_id} className="px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="text-sm font-medium text-ink">{subject.subject_name}</p>
                        <p className="text-[11px] text-muted">{subject.subject_code}</p>
                      </div>
                      <span className="text-sm font-semibold text-ink">
                        {subject.percentage === null ? "—" : `${subject.percentage}%`}
                      </span>
                    </div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-[#EDF1F7]">
                      <div
                        className="h-full rounded-full bg-brand"
                        style={{ width: `${Math.min(100, subject.percentage ?? 0)}%` }}
                      />
                    </div>
                    <p className="mt-1 text-[10px] text-muted">
                      {subject.present} present of {subject.sessions} held
                    </p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card className="mt-4">
            <CardHeader
              title="Recent attendance"
              action={
                <Link href="/student/attendance" className="text-xs font-semibold text-brand hover:underline">
                  View all
                </Link>
              }
            />
            {!data.recent_records.length ? (
              <EmptyState
                icon={<Clock3 size={20} />}
                title="No attendance records yet"
                description="Records appear after you complete a verified check-in."
              />
            ) : (
              <ul className="divide-y divide-line">
                {data.recent_records.map((record) => (
                  <li key={record.record_id} className="flex items-center justify-between gap-3 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-ink">{record.subject_name}</p>
                      <p className="text-[11px] text-muted">{formatDateTime(record.session_starts_at)}</p>
                    </div>
                    <Badge tone={statusTone(record.status)}>{titleCase(record.status)}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <div className="mt-4 flex items-start gap-2 rounded-xl border border-line bg-white p-4 text-[11px] leading-relaxed text-muted">
            <CheckCircle2 size={14} className="mt-0.5 shrink-0 text-[#12855A]" />
            A check-in verifies the required factors for this session. If evidence is missing or a
            provider is unavailable, your case may go to teacher review instead of being accepted or
            labelled dishonest automatically.
          </div>
        </>
      ) : null}
    </div>
  );
}
