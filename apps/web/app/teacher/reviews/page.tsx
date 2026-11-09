"use client";

import { CheckCircle2, ListChecks, XCircle } from "lucide-react";
import { useMemo, useState } from "react";
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
import type { Review } from "@/lib/types";

export default function TeacherReviewsPage() {
  const [filter, setFilter] = useState<"open" | "all">("open");
  const path = filter === "open" ? "/teacher/reviews?status=open" : "/teacher/reviews";
  const reviews = useApiData<Review[]>(path);
  const [selected, setSelected] = useState<Review | null>(null);
  const [note, setNote] = useState("");
  const [decision, setDecision] = useState<"approved" | "rejected">("approved");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openCount = useMemo(
    () => (reviews.data ?? []).filter((review) => review.status === "open").length,
    [reviews.data],
  );

  async function submit() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/teacher/reviews/${selected.id}/resolve`, {
        method: "POST",
        body: JSON.stringify({ decision, note }),
      });
      setSelected(null);
      setNote("");
      await reviews.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Review queue"
        title="Verification reviews"
        description="Attempts that could not be accepted automatically. Missing permission or an unavailable provider is never treated as proof of misconduct."
        actions={
          <div className="flex rounded-lg border border-line bg-white p-0.5">
            {(["open", "all"] as const).map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                className={
                  filter === value
                    ? "rounded-md bg-active px-3 py-1.5 text-xs font-semibold text-brand"
                    : "rounded-md px-3 py-1.5 text-xs font-medium text-muted hover:text-ink"
                }
              >
                {value === "open" ? `Open (${openCount})` : "All"}
              </button>
            ))}
          </div>
        }
      />

      {error ? (
        <div className="mb-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}

      {reviews.loading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-40" />
          <Skeleton className="h-40" />
        </div>
      ) : !reviews.data?.length ? (
        <Card>
          <EmptyState
            icon={<ListChecks size={22} />}
            title={filter === "open" ? "No open reviews" : "No reviews yet"}
            description="Risk-engine outcomes that require human judgement appear here with their reason codes."
          />
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {reviews.data.map((review) => (
            <Card key={review.id} className="p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-ink">{review.student_name}</p>
                  <p className="text-[11px] text-muted">
                    {review.roll_number} · {review.subject_name} · {review.class_name}
                  </p>
                </div>
                <Badge tone={statusTone(review.status)}>{titleCase(review.status)}</Badge>
              </div>
              <p className="mt-3 rounded-lg bg-[#FAFBFD] px-3 py-2 text-xs leading-relaxed text-[#475467]">
                {review.reason}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {review.risk_decision ? (
                  <Badge tone={statusTone(review.risk_decision)}>{review.risk_decision}</Badge>
                ) : null}
                {review.risk_score !== null ? (
                  <Badge tone="neutral">risk points {review.risk_score}</Badge>
                ) : null}
                {(review.risk_reasons ?? [])
                  .filter((reason) => reason.severity !== "info")
                  .map((reason) => (
                    <Badge key={`${review.id}-${reason.code}`} tone="amber">
                      {reason.code}
                    </Badge>
                  ))}
              </div>
              <div className="mt-4 flex items-center justify-between gap-3">
                <p className="text-[11px] text-muted">
                  Session {formatDateTime(review.session_starts_at)}
                </p>
                {review.status === "open" ? (
                  <Button
                    size="sm"
                    onClick={() => {
                      setSelected(review);
                      setDecision("approved");
                      setNote("");
                      setError(null);
                    }}
                  >
                    Review decision
                  </Button>
                ) : (
                  <span className="text-[11px] text-muted">
                    Resolved {formatDateTime(review.resolved_at)}
                  </span>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Modal
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        title="Record a review decision"
        description="The decision, note and any attendance correction are stored in the audit trail."
        size="md"
      >
        {selected ? (
          <div className="space-y-4">
            <div className="rounded-lg bg-[#FAFBFD] p-3 text-xs text-[#475467]">
              <p className="font-semibold text-ink">{selected.student_name}</p>
              <p>
                {selected.roll_number} · {selected.subject_name}
              </p>
              <p className="mt-1">{selected.reason}</p>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setDecision("approved")}
                className={
                  decision === "approved"
                    ? "rounded-lg border border-[#ABEFC6] bg-[#F3FCF7] px-3 py-2 text-xs font-semibold text-[#067647]"
                    : "rounded-lg border border-line px-3 py-2 text-xs font-medium text-muted"
                }
              >
                <CheckCircle2 size={14} className="mr-1 inline" /> Approve attendance
              </button>
              <button
                type="button"
                onClick={() => setDecision("rejected")}
                className={
                  decision === "rejected"
                    ? "rounded-lg border border-[#FECDCA] bg-[#FFF5F4] px-3 py-2 text-xs font-semibold text-[#B42318]"
                    : "rounded-lg border border-line px-3 py-2 text-xs font-medium text-muted"
                }
              >
                <XCircle size={14} className="mr-1 inline" /> Mark absent
              </button>
            </div>
            <Field label="Decision note" hint="Required. Explain the evidence you considered." required>
              <Textarea
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="e.g. Student reported low GPS accuracy indoors; attendance confirmed against the session PIN and classroom observation."
              />
            </Field>
            {error ? <Alert tone="danger">{error}</Alert> : null}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setSelected(null)}>
                Cancel
              </Button>
              <Button onClick={() => void submit()} loading={busy} disabled={note.trim().length < 3}>
                Save decision
              </Button>
            </div>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
