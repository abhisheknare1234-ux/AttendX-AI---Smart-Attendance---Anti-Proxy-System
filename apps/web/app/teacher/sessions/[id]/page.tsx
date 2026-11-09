"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Copy,
  KeyRound,
  Lock,
  MapPin,
  PlayCircle,
  QrCode,
  RefreshCw,
  ScanFace,
  StopCircle,
  UsersRound,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  Modal,
  PageHeader,
  Skeleton,
  StatCard,
  statusTone,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useCountdown } from "@/hooks/use-api-data";
import { api, errorMessage, formatDateTime, formatSeconds, titleCase } from "@/lib/api";
import type { LiveSessionResponse, OpenSessionResponse } from "@/lib/types";
import { QrSvg } from "@/components/qr";

export default function TeacherSessionLivePage() {
  const params = useParams<{ id: string }>();
  const sessionId = params.id;
  const [live, setLive] = useState<LiveSessionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [pin, setPin] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [confirmClose, setConfirmClose] = useState(false);
  const statusRef = useRef<string>("");

  const loadLive = useCallback(async () => {
    try {
      const data = await api<LiveSessionResponse>(`/teacher/sessions/${sessionId}/live`);
      setLive(data);
      statusRef.current = data.session.status;
      setError(null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    void loadLive();
    const timer = window.setInterval(() => {
      if (statusRef.current === "open") void loadLive();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [loadLive]);

  const sessionRemaining = useCountdown(live?.session.ends_at);
  const qrRemaining = useCountdown(live?.qr?.expires_at);

  async function openSession() {
    setBusy("open");
    setError(null);
    try {
      const result = await api<OpenSessionResponse>(`/teacher/sessions/${sessionId}/open`, {
        method: "POST",
      });
      setPin(result.pin);
      statusRef.current = "open";
      await loadLive();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function closeSession() {
    setBusy("close");
    try {
      await api(`/teacher/sessions/${sessionId}/close`, { method: "POST" });
      setConfirmClose(false);
      setPin(null);
      await loadLive();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function regeneratePin() {
    setBusy("pin");
    setError(null);
    try {
      const result = await api<{ pin: string }>(`/teacher/sessions/${sessionId}/pin/regenerate`, {
        method: "POST",
      });
      setPin(result.pin);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function copyLink() {
    if (!live?.qr?.url) return;
    try {
      await navigator.clipboard.writeText(live.qr.url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopied(false);
    }
  }

  if (loading && !live) {
    return (
      <div>
        <Skeleton className="mb-6 h-16" />
        <div className="grid gap-4 lg:grid-cols-3">
          <Skeleton className="h-96 lg:col-span-2" />
          <Skeleton className="h-96" />
        </div>
      </div>
    );
  }

  if (!live && error) {
    return (
      <div className="mx-auto max-w-xl">
        <Alert tone="danger" title="Session could not be loaded">
          {error}
        </Alert>
        <Link href="/teacher/sessions" className="mt-4 inline-block text-sm text-brand hover:underline">
          Back to sessions
        </Link>
      </div>
    );
  }

  if (!live) return null;
  const session = live.session;
  const isOpen = session.status === "open";
  const isClosed = ["closed", "expired", "cancelled"].includes(session.status);

  return (
    <div>
      <Link href="/teacher/sessions" className="mb-4 inline-flex items-center gap-1 text-xs font-medium text-muted hover:text-brand">
        <ArrowLeft size={14} /> All sessions
      </Link>
      <PageHeader
        eyebrow={`${session.class_name} · ${session.subject_name}`}
        title={`${session.subject_name} attendance`}
        description={`${session.classroom_name} · window ${Math.round(session.window_seconds / 60)} min · QR rotates every ${session.qr_refresh_seconds}s`}
        actions={
          isOpen ? (
            <Button variant="danger" onClick={() => setConfirmClose(true)}>
              <StopCircle size={15} /> Close session
            </Button>
          ) : null
        }
      />

      {error ? (
        <div className="mb-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Badge tone={statusTone(session.status)}>{titleCase(session.status)}</Badge>
        {session.require_pin ? <Badge tone="blue">PIN</Badge> : null}
        {session.require_geofence ? <Badge tone="blue">Location</Badge> : null}
        {session.require_face ? <Badge tone="blue">Face</Badge> : null}
        {session.require_liveness ? <Badge tone="blue">Liveness</Badge> : null}
        <span className="text-xs text-muted">Created {formatDateTime(session.starts_at)}</span>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.35fr_1fr]">
        <Card>
          <CardHeader
            title={isOpen ? "Live attendance window" : "Attendance window"}
            description={
              isOpen
                ? `Closes in ${formatSeconds(sessionRemaining)} · QR token refreshes in ${formatSeconds(qrRemaining)}`
                : isClosed
                  ? "This session is closed. The QR and PIN are no longer valid."
                  : "Open the session when you are ready for students to check in."
            }
            action={
              isOpen ? (
                <Button variant="secondary" size="sm" onClick={() => void regeneratePin()} loading={busy === "pin"}>
                  <KeyRound size={14} /> Regenerate PIN
                </Button>
              ) : null
            }
          />

          {isOpen ? (
            <div className="grid gap-6 p-5 sm:grid-cols-[auto_1fr]">
              <div className="mx-auto rounded-2xl border border-line bg-white p-3 shadow-sm" data-testid="attendance-qr">
                <QrSvg value={live.qr?.url} size={248} />
                <p className="mt-2 text-center text-[10px] text-muted">
                  Signed token · expires in {formatSeconds(qrRemaining)}
                </p>
              </div>
              <div className="space-y-4">
                <div className="rounded-xl border border-line bg-[#FAFBFD] p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Temporary PIN
                  </p>
                  {pin ? (
                    <p data-testid="session-pin" className="mt-1 font-mono text-3xl font-bold tracking-[0.2em] text-ink">
                      {pin}
                    </p>
                  ) : (
                    <div>
                      <p className="mt-1 text-sm font-semibold text-ink">PIN hidden</p>
                      <p className="mt-0.5 text-xs text-muted">
                        For security, the PIN is only shown when generated. Regenerate it to display
                        it again; students who already verified are unaffected.
                      </p>
                    </div>
                  )}
                </div>
                <div className="rounded-xl border border-line p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">
                    Session link
                  </p>
                  <div className="mt-1 flex items-start justify-between gap-2">
                    <p data-testid="session-link" className="break-all text-[11px] leading-relaxed text-ink">{live.qr?.url}</p>
                    <Button variant="ghost" size="sm" onClick={() => void copyLink()}>
                      {copied ? <CheckCircle2 size={14} /> : <Copy size={14} />}
                    </Button>
                  </div>
                  <p className="mt-2 text-[11px] text-muted">
                    Students can scan the QR with their phone camera or use the in-browser scanner.
                  </p>
                </div>
                <div className="flex items-center gap-2 rounded-lg border border-[#ABEFC6] bg-[#F3FCF7] px-3 py-2 text-[11px] text-[#05603A]">
                  <Lock size={13} /> The PIN is never written to logs. Closing the session clears it
                  server-side.
                </div>
              </div>
            </div>
          ) : isClosed ? (
            <EmptyState
              icon={<Lock size={20} />}
              title="Session closed"
              description="QR tokens were revoked and the PIN is invalid. Attendance records remain available in reports and the review queue."
              action={
                <Link href="/teacher/sessions/new">
                  <Button size="sm">
                    <PlayCircle size={14} /> Start a new session
                  </Button>
                </Link>
              }
            />
          ) : (
            <div className="p-5">
              <div className="rounded-xl border border-[#D4E3FF] bg-[#F5F9FF] p-5">
                <h3 className="text-sm font-semibold text-ink">Ready to open?</h3>
                <p className="mt-1 text-xs leading-relaxed text-[#1F3D7A]">
                  Opening starts the {Math.round(session.window_seconds / 60)}-minute check-in
                  window and creates the first signed QR token and temporary PIN. This action is
                  audited.
                </p>
                <Button className="mt-4" onClick={() => void openSession()} loading={busy === "open"} data-testid="open-session">
                  <PlayCircle size={16} /> Open session now
                </Button>
              </div>
            </div>
          )}
        </Card>

        <div className="grid grid-cols-2 gap-3 content-start">
          <StatCard
            label="Eligible"
            value={session.eligible_students}
            icon={<UsersRound size={17} />}
          />
          <StatCard
            label="Accepted"
            value={session.accepted}
            tone="green"
            icon={<CheckCircle2 size={17} />}
            testId="accepted-count"
          />
          <StatCard
            label="Pending steps"
            value={session.pending}
            tone="amber"
            icon={<Clock3 size={17} />}
          />
          <StatCard
            label="Review required"
            value={session.review_required}
            tone={session.review_required ? "amber" : "blue"}
            icon={<AlertTriangle size={17} />}
          />
          <StatCard
            label="Rejected"
            value={session.rejected}
            tone={session.rejected ? "red" : "blue"}
            icon={<AlertTriangle size={17} />}
          />
          <StatCard
            label="Seconds left"
            value={isOpen ? formatSeconds(sessionRemaining) : "—"}
            icon={<Clock3 size={17} />}
            tone="purple"
          />
        </div>
      </div>

      <Card className="mt-5">
        <CardHeader
          title="Live check-in activity"
          description="Most recent attempts. Factor states are reported exactly as recorded by the backend."
        />
        {!live.recent_attempts.length ? (
          <EmptyState
            icon={<QrCode size={20} />}
            title="Waiting for the first check-in"
            description={
              isOpen
                ? "Students who scan the current QR and complete the required steps will appear here."
                : "Open the session to accept check-ins."
            }
          />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Student</Th>
                  <Th>Status</Th>
                  <Th className="hidden md:table-cell">Location</Th>
                  <Th className="hidden md:table-cell">Identity</Th>
                  <Th>Risk</Th>
                  <Th className="hidden sm:table-cell">Started</Th>
                </tr>
              </thead>
              <tbody>
                {live.recent_attempts.map((attempt) => (
                  <tr key={attempt.attempt_id}>
                    <Td>
                      <p className="font-medium text-ink">{attempt.student_name}</p>
                      <p className="text-[11px] text-muted">{attempt.roll_number}</p>
                    </Td>
                    <Td>
                      <Badge tone={statusTone(attempt.status)}>{titleCase(attempt.status)}</Badge>
                    </Td>
                    <Td className="hidden md:table-cell">
                      <StatusChip value={attempt.gps_status} />
                    </Td>
                    <Td className="hidden md:table-cell">
                      <div className="flex flex-wrap gap-1">
                        <StatusChip value={attempt.face_status} label="Face" />
                        <StatusChip value={attempt.liveness_status} label="Live" />
                      </div>
                    </Td>
                    <Td>
                      {attempt.risk_decision ? (
                        <Badge tone={statusTone(attempt.risk_decision)}>
                          {titleCase(attempt.risk_decision)}
                        </Badge>
                      ) : (
                        <span className="text-xs text-muted">—</span>
                      )}
                    </Td>
                    <Td className="hidden whitespace-nowrap text-xs text-muted sm:table-cell">
                      {formatDateTime(attempt.created_at)}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <div className="mt-5 flex flex-wrap items-center gap-2 text-xs text-muted">
        <MapPin size={14} /> Geofence is evaluated server-side against the classroom centre and
        radius. Browser GPS is treated as evidence, not proof.
        <Link href="/teacher/reviews" className="font-semibold text-brand hover:underline">
          Review flagged attempts
        </Link>
      </div>

      <Modal
        open={confirmClose}
        onClose={() => setConfirmClose(false)}
        title="Close this attendance session?"
        description="Closing is server-authoritative: QR tokens are revoked, the PIN is cleared and in-progress attempts are marked abandoned."
        size="sm"
      >
        <div className="space-y-4">
          <Alert tone="warning">
            Students who have not completed verification will need a teacher review or a new
            session. This action is recorded in the audit log.
          </Alert>
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setConfirmClose(false)}>
              Keep open
            </Button>
            <Button variant="danger" onClick={() => void closeSession()} loading={busy === "close"}>
              <StopCircle size={15} /> Close session
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

function StatusChip({ value, label }: { value: string; label?: string }) {
  const tone = statusTone(value);
  return (
    <Badge tone={tone}>
      {label ? `${label}: ` : ""}
      {titleCase(value)}
    </Badge>
  );
}
