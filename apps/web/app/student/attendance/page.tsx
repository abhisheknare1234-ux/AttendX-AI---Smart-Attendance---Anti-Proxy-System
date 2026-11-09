"use client";

import Link from "next/link";
import { CalendarClock, MessageSquarePlus, QrCode } from "lucide-react";
import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  EmptyState,
  Field,
  Modal,
  PageHeader,
  Skeleton,
  Textarea,
  statusTone,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage, formatDateTime, titleCase } from "@/lib/api";
import type { HistoryItem } from "@/lib/types";

export default function StudentHistoryPage() {
  const history = useApiData<HistoryItem[]>("/student/attendance?limit=200");
  const [selected, setSelected] = useState<HistoryItem | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function submitReview() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api("/student/review-requests", {
        method: "POST",
        body: JSON.stringify({ session_id: selected.session_id, reason }),
      });
      setSelected(null);
      setReason("");
      setMessage("Your review request was submitted. A teacher will see it in their review queue.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Attendance history"
        title="Your attendance records"
        description="Every accepted, review-required or rejected decision, with its reference and session context."
        actions={
          <Link href="/student/scan">
            <Button size="sm">
              <QrCode size={14} /> Scan attendance
            </Button>
          </Link>
        }
      />

      {message ? (
        <div className="mb-4">
          <Alert tone="success">{message}</Alert>
        </div>
      ) : null}

      {history.loading ? (
        <div className="space-y-3">
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </div>
      ) : history.error ? (
        <Alert tone="danger">{history.error}</Alert>
      ) : !history.data?.length ? (
        <Card>
          <EmptyState
            icon={<CalendarClock size={22} />}
            title="No attendance records yet"
            description="Once you complete a verified check-in, the decision and its reference appear here."
            action={
              <Link href="/student/scan">
                <Button size="sm">Scan a session QR</Button>
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {history.data.map((record) => (
            <Card key={record.record_id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-ink">{record.subject_name}</p>
                  <p className="text-[11px] text-muted">
                    {record.subject_code} · {record.class_name}
                  </p>
                </div>
                <Badge tone={statusTone(record.status)}>{titleCase(record.status)}</Badge>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-muted">
                <p>
                  <span className="block text-[10px] uppercase tracking-wide">Session</span>
                  {formatDateTime(record.session_starts_at)}
                </p>
                <p>
                  <span className="block text-[10px] uppercase tracking-wide">Check-in</span>
                  {record.check_in_at ? formatDateTime(record.check_in_at) : "Not accepted"}
                </p>
                <p className="col-span-2">
                  <span className="block text-[10px] uppercase tracking-wide">Reference</span>
                  <span className="font-mono text-ink">{record.reference}</span>
                </p>
              </div>
              <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
                <span className="text-[10px] text-muted">
                  Classification: {titleCase(record.classification)} · {titleCase(record.decision_source)}
                </span>
                {["review_required", "rejected", "absent"].includes(record.status) ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => {
                      setSelected(record);
                      setReason("");
                      setError(null);
                    }}
                  >
                    <MessageSquarePlus size={14} /> Request review
                  </Button>
                ) : null}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="Request a teacher review"
        description="Explain what happened so the teacher can check the recorded evidence."
        size="md"
      >
        {selected ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-[#FAFBFD] p-3 text-xs text-[#475467]">
              <p className="font-semibold text-ink">{selected.subject_name}</p>
              <p>
                {formatDateTime(selected.session_starts_at)} · {titleCase(selected.status)}
              </p>
            </div>
            <Field
              label="Context for your teacher"
              hint="Do not include passwords or sensitive personal data."
              required
            >
              <Textarea
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="e.g. My location permission was denied during the lecture; I was present in room 101 and asked the teacher after class."
              />
            </Field>
            {error ? <Alert tone="danger">{error}</Alert> : null}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setSelected(null)}>
                Cancel
              </Button>
              <Button onClick={() => void submitReview()} loading={busy} disabled={reason.trim().length < 10}>
                Submit request
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
