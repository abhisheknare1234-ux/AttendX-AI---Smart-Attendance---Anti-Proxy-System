"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  QrCode,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { RequireRole } from "@/components/guard";
import { StudentShell } from "@/components/shell";
import { CheckInFlow } from "@/components/check-in-flow";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Skeleton,
  statusTone,
} from "@/components/ui";
import { studentNav } from "@/app/student/layout";
import { api, errorMessage, formatDateTime } from "@/lib/api";
import type { CheckInResponse, QrValidateResponse } from "@/lib/types";

export default function AttendPage() {
  return (
    <RequireRole roles={["student"]}>
      <StudentShell nav={studentNav}>
        <AttendContent />
      </StudentShell>
    </RequireRole>
  );
}

function AttendContent() {
  const params = useParams<{ token: string }>();
  const token = typeof params.token === "string" ? decodeURIComponent(params.token) : "";
  const [session, setSession] = useState<QrValidateResponse | null>(null);
  const [checkIn, setCheckIn] = useState<CheckInResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function validate() {
      if (!token) {
        setError("This attendance link is missing a session token.");
        setLoading(false);
        return;
      }
      try {
        const result = await api<QrValidateResponse>("/attendance/qr/validate", {
          method: "POST",
          body: JSON.stringify({ token }),
        });
        if (!cancelled) setSession(result);
      } catch (caught) {
        if (!cancelled) setError(errorMessage(caught));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void validate();
    return () => {
      cancelled = true;
    };
  }, [token]);

  async function begin() {
    setStarting(true);
    setError(null);
    try {
      const result = await api<CheckInResponse>("/attendance/check-ins", {
        method: "POST",
        body: JSON.stringify({ qr_token: token }),
      });
      setCheckIn(result);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setStarting(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-40" />
        <Skeleton className="h-24" />
      </div>
    );
  }

  if (error && !session) {
    return (
      <div>
        <Link href="/student/scan" className="mb-3 inline-flex items-center gap-1 text-xs text-muted hover:text-brand">
          <ArrowLeft size={14} /> Back to scanner
        </Link>
        <Alert tone="danger" title="This attendance link cannot be used">
          {error}
        </Alert>
        <Card className="mt-4">
          <EmptyState
            icon={<QrCode size={22} />}
            title="Scan the current QR"
            description="Attendance QR codes are short-lived and bound to an open session. Ask your teacher to show the current code, then scan or paste that link."
            action={
              <Link href="/student/scan">
                <Button size="sm">Open scanner</Button>
              </Link>
            }
          />
        </Card>
      </div>
    );
  }

  if (checkIn) {
    return (
      <div>
        <Link href="/student/scan" className="mb-3 inline-flex items-center gap-1 text-xs text-muted hover:text-brand">
          <ArrowLeft size={14} /> Leave check-in
        </Link>
        <CheckInFlow initial={checkIn} />
      </div>
    );
  }

  if (!session) return null;

  return (
    <div>
      <Link href="/student/scan" className="mb-3 inline-flex items-center gap-1 text-xs text-muted hover:text-brand">
        <ArrowLeft size={14} /> Back to scanner
      </Link>

      <Card className="overflow-hidden">
        <div className="bg-brand px-5 py-5 text-white">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#BFD3FF]">
                Attendance session
              </p>
              <h1 className="mt-1 text-xl font-semibold">{session.subject_name}</h1>
              <p className="text-xs text-[#D7E4FF]">
                {session.class_name} · {session.teacher_name}
              </p>
            </div>
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15">
              <ShieldCheck size={20} />
            </span>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-full bg-white/15 px-2.5 py-1">
              <Clock3 size={11} className="mr-1 inline" /> {Math.max(0, Math.round(session.seconds_remaining / 60))} min remaining
            </span>
            <span className="rounded-full bg-white/15 px-2.5 py-1">{session.classroom_name}</span>
          </div>
        </div>

        <div className="space-y-4 p-5">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
              Required verification
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {session.requirements.pin ? <Badge tone="blue">PIN</Badge> : null}
              {session.requirements.geofence ? <Badge tone="blue">Location</Badge> : null}
              {session.requirements.face ? <Badge tone="blue">Face</Badge> : null}
              {session.requirements.liveness ? <Badge tone="blue">Liveness</Badge> : null}
            </div>
          </div>

          <div className="rounded-lg border border-line bg-[#FAFBFD] p-3 text-xs leading-relaxed text-[#475467]">
            <p>
              <strong className="font-semibold text-ink">Session window:</strong>{" "}
              {formatDateTime(session.starts_at)} → {formatDateTime(session.ends_at)}
            </p>
            <p className="mt-1">{session.message}</p>
          </div>

          {error ? <Alert tone="danger">{error}</Alert> : null}

          {session.already_recorded ? (
            <div className="rounded-xl border border-line p-4">
              <p className="flex items-center gap-2 text-sm font-semibold text-ink">
                <CheckCircle2 size={16} className="text-[#12855A]" /> Attendance already recorded
              </p>
              {session.existing_status ? (
                <p className="mt-1">
                  <Badge tone={statusTone(session.existing_status)}>{session.existing_status}</Badge>
                </p>
              ) : null}
              <Link href="/student/attendance" className="mt-3 inline-block text-xs font-semibold text-brand hover:underline">
                View your attendance history
              </Link>
            </div>
          ) : session.can_check_in ? (
            <Button className="w-full" size="lg" onClick={() => void begin()} loading={starting}>
              <ShieldCheck size={17} /> Begin verified check-in
            </Button>
          ) : (
            <Alert tone="warning" title="Check-in is not available">
              {session.status === "scheduled"
                ? "Your teacher has not opened this session yet. Keep this page or scan again once it is open."
                : "This session is closed. A new attendance session is required."}
            </Alert>
          )}

          <div className="flex items-start gap-2 text-[11px] leading-relaxed text-muted">
            <AlertTriangle size={13} className="mt-0.5 shrink-0 text-[#B54708]" />
            The QR link only identifies the session. Your attendance is not marked until every
            required factor is submitted and the backend makes the decision.
          </div>
        </div>
      </Card>
    </div>
  );
}
