"use client";

import Link from "next/link";
import {
  AlertTriangle,
  CheckCircle2,
  Clock3,
  LocateFixed,
  Lock,
  MapPin,
  ScanFace,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  DefinitionRow,
  Input,
  statusTone,
} from "@/components/ui";
import { useCountdown } from "@/hooks/use-api-data";
import { api, errorMessage, formatDateTime, formatSeconds, titleCase } from "@/lib/api";
import type {
  Attempt,
  CheckInResponse,
  FactorStepResponse,
  FinalizeResponse,
  LocationStepResponse,
  StepResponse,
} from "@/lib/types";

type StepKey = "pin" | "gps" | "face" | "liveness";

const STEP_META: Record<StepKey, { label: string; icon: typeof Lock; description: string }> = {
  pin: { label: "Temporary PIN", icon: Lock, description: "Enter the PIN displayed by your teacher." },
  gps: { label: "Location evidence", icon: MapPin, description: "Share a location fix for this check-in only." },
  face: { label: "Face verification", icon: ScanFace, description: "A provider check, when configured and authorized." },
  liveness: { label: "Liveness", icon: ShieldCheck, description: "A separate replay-resistance check, when configured." },
};

function stepState(attempt: Attempt, key: StepKey): "done" | "failed" | "pending" | "review" {
  const value =
    key === "pin"
      ? attempt.pin_status
      : key === "gps"
        ? attempt.gps_status
        : key === "face"
          ? attempt.face_status
          : attempt.liveness_status;
  if (["PASSED", "INSIDE_GEOFENCE", "NOT_REQUIRED"].includes(value)) return "done";
  if (["FAILED", "OUTSIDE_GEOFENCE", "LOW_ACCURACY", "PERMISSION_DENIED", "UNAVAILABLE", "STALE", "REVIEW_REQUIRED"].includes(value)) return "review";
  if (["PENDING", "PENDING_REVIEW", "NOT_SUBMITTED"].includes(value)) return "pending";
  return "pending";
}

export function CheckInFlow({ initial }: { initial: CheckInResponse }) {
  const [attempt, setAttempt] = useState<Attempt>(initial.attempt);
  const session = initial.session;
  const [next, setNext] = useState<string | null>(initial.next_step);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [pin, setPin] = useState("");
  const [final, setFinal] = useState<FinalizeResponse | null>(null);
  const [factorMessage, setFactorMessage] = useState<string | null>(null);

  const remaining = useCountdown(session.ends_at);

  function applyAttempt(updated: Attempt, nextStep: string | null) {
    setAttempt(updated);
    setNext(nextStep);
    if (nextStep === null) setNotice("All required steps are recorded. Finalize to receive the server decision.");
  }

  async function submitPin() {
    setBusy("pin");
    setError(null);
    try {
      const response = await api<StepResponse>(`/attendance/attempts/${attempt.id}/pin`, {
        method: "POST",
        body: JSON.stringify({ pin }),
      });
      applyAttempt(response.attempt, response.next_step);
      setNotice("PIN verified by the server.");
      setPin("");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function submitLocation() {
    setBusy("gps");
    setError(null);
    setNotice(null);
    const send = async (payload: Record<string, unknown>) => {
      try {
        const response = await api<LocationStepResponse>(
          `/attendance/attempts/${attempt.id}/location`,
          { method: "POST", body: JSON.stringify(payload) },
        );
        applyAttempt(response.attempt, response.next_step);
        const distance =
          response.distance_m === null ? "" : ` Distance from classroom centre: ${response.distance_m} m.`;
        const accuracy =
          response.accuracy_m === null ? "" : ` Reported accuracy: ${response.accuracy_m} m.`;
        setFactorMessage(`${titleCase(response.gps_status)}.${distance}${accuracy}`);
        if (response.reason_code) {
          setFactorMessage((previous) => `${previous} Reason: ${response.reason_code}.`);
        }
      } catch (caught) {
        setError(errorMessage(caught));
      } finally {
        setBusy(null);
      }
    };

    if (!navigator.geolocation) {
      await send({ unavailable: true, permission_denied: false });
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void send({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy_m: position.coords.accuracy,
          client_timestamp: new Date(position.timestamp).toISOString(),
          permission_denied: false,
          unavailable: false,
        });
      },
      (geoError) => {
        const denied = geoError.code === geoError.PERMISSION_DENIED;
        void send({
          permission_denied: denied,
          unavailable: !denied,
          latitude: null,
          longitude: null,
          accuracy_m: null,
        });
      },
      { enableHighAccuracy: true, timeout: 20000, maximumAge: 0 },
    );
  }

  async function submitFactor(kind: "face" | "liveness", file: File | null) {
    setBusy(kind);
    setError(null);
    setFactorMessage(null);
    try {
      const form = new FormData();
      if (file) form.append("image", file);
      const response = await api<FactorStepResponse>(
        `/attendance/attempts/${attempt.id}/${kind}`,
        { method: "POST", body: form },
      );
      applyAttempt(response.attempt, response.next_step);
      const provider = response.provider ? ` Provider: ${response.provider}.` : "";
      const score = response.score === null ? "" : ` Score: ${response.score.toFixed(3)}.`;
      const reason = response.reason_code ? ` Reason: ${response.reason_code}.` : "";
      setFactorMessage(`${titleCase(response.status)}.${reason}${provider}${score}`);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function finalize() {
    setBusy("finalize");
    setError(null);
    try {
      const response = await api<FinalizeResponse>(
        `/attendance/attempts/${attempt.id}/finalize`,
        { method: "POST" },
      );
      setFinal(response);
      setAttempt((current) => ({
        ...current,
        status:
          response.decision === "ACCEPTED"
            ? "accepted"
            : response.decision === "REVIEW_REQUIRED"
              ? "review_required"
              : "rejected",
        risk_decision: response.decision,
        risk_score: response.risk_score,
        risk_reasons: response.reasons,
      }));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  if (final) {
    const accepted = final.decision === "ACCEPTED";
    const review = final.decision === "REVIEW_REQUIRED";
    return (
      <Card className="overflow-hidden">
        <div
          className={
            accepted
              ? "bg-[#F3FCF7] px-6 py-8 text-center"
              : review
                ? "bg-[#FFFCF2] px-6 py-8 text-center"
                : "bg-[#FFF5F4] px-6 py-8 text-center"
          }
        >
          <span
            className={
              accepted
                ? "mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#12855A] text-white"
                : review
                  ? "mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#B54708] text-white"
                  : "mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-[#B42318] text-white"
            }
          >
            {accepted ? <CheckCircle2 size={28} /> : review ? <AlertTriangle size={28} /> : <XCircle size={28} />}
          </span>
          <h2 className="mt-4 text-xl font-semibold text-ink" data-testid="attendance-result">
            {accepted
              ? "Attendance confirmed"
              : review
                ? "Sent for teacher review"
                : "Attendance not accepted"}
          </h2>
          <p className="mx-auto mt-1 max-w-sm text-sm text-muted">
            {accepted
              ? "The backend accepted every required factor for this session and recorded your attendance."
              : review
                ? "Some evidence could not be verified automatically. Your teacher will review the recorded reason codes; this is not an accusation."
                : "The server rejected this attendance attempt based on the recorded evidence."}
          </p>
          <div className="mx-auto mt-4 inline-flex items-center gap-2 rounded-lg border border-line bg-white px-4 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">Reference</span>
            <span className="font-mono text-sm font-semibold text-ink">{final.reference}</span>
          </div>
        </div>
        <div className="px-6 py-5">
          <DefinitionRow label="Decision" value={titleCase(final.decision)} />
          <DefinitionRow label="Attendance status" value={titleCase(final.status)} />
          <DefinitionRow label="Classification" value={titleCase(final.classification)} />
          <DefinitionRow label="Decision source" value={titleCase(final.decision_source)} />
          <DefinitionRow label="Risk points" value={final.risk_score} />
          <DefinitionRow label="Check-in time" value={formatDateTime(final.check_in_at)} />
          {final.reasons.filter((reason) => reason.severity !== "info").length ? (
            <div className="mt-3 rounded-lg border border-line bg-[#FAFBFD] p-3">
              <p className="text-[10px] font-semibold uppercase tracking-wide text-muted">Reason codes</p>
              <ul className="mt-1.5 space-y-1">
                {final.reasons
                  .filter((reason) => reason.severity !== "info")
                  .map((reason) => (
                    <li key={`${reason.code}-${reason.factor}`} className="text-xs text-[#475467]">
                      <span className="font-mono text-[10px] text-brand">{reason.code}</span> ·{" "}
                      {reason.message}
                    </li>
                  ))}
              </ul>
            </div>
          ) : null}
          <div className="mt-4 grid grid-cols-2 gap-2">
            <Link href="/student/attendance">
              <Button variant="secondary" className="w-full">
                View history
              </Button>
            </Link>
            <Link href="/student">
              <Button className="w-full">Back home</Button>
            </Link>
          </div>
          {review ? (
            <p className="mt-3 text-center text-[11px] text-muted">
              You can add a review request with context from your history page.
            </p>
          ) : null}
        </div>
      </Card>
    );
  }

  const steps = initial.required_steps as StepKey[];

  return (
    <div className="space-y-4">
      <Card className="overflow-hidden">
        <div className="bg-brand px-5 py-4 text-white">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[#BFD3FF]">
                Verified check-in
              </p>
              <p className="mt-1 text-lg font-semibold">{session.subject_name}</p>
              <p className="text-xs text-[#D7E4FF]">
                {session.class_name} · {session.teacher_name}
              </p>
            </div>
            <Badge tone="neutral" className="border-white/30 bg-white/15 text-white">
              <Clock3 size={11} /> {formatSeconds(remaining)}
            </Badge>
          </div>
        </div>
        <div className="px-4 py-3">
          <div className="space-y-2">
            {steps.map((key) => {
              const meta = STEP_META[key];
              const state = stepState(attempt, key);
              const Icon = meta.icon;
              const active = next === key;
              return (
                <div
                  key={key}
                  className={
                    active
                      ? "flex items-center gap-3 rounded-lg border border-brand/30 bg-[#F5F9FF] px-3 py-2"
                      : "flex items-center gap-3 rounded-lg border border-line px-3 py-2"
                  }
                >
                  <span
                    className={
                      state === "done"
                        ? "flex h-7 w-7 items-center justify-center rounded-full bg-[#ECFDF3] text-[#067647]"
                        : state === "review"
                          ? "flex h-7 w-7 items-center justify-center rounded-full bg-[#FFFAEB] text-[#B54708]"
                          : "flex h-7 w-7 items-center justify-center rounded-full bg-[#F2F4F8] text-muted"
                    }
                  >
                    {state === "done" ? <CheckCircle2 size={15} /> : <Icon size={14} />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-ink">{meta.label}</p>
                    <p className="text-[10px] text-muted">{meta.description}</p>
                  </div>
                  <Badge tone={state === "done" ? "green" : state === "review" ? "amber" : "neutral"}>
                    {state === "done" ? "Done" : state === "review" ? "Recorded" : active ? "Now" : "Pending"}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      </Card>

      {error ? (
        <Alert tone="danger" title="Step could not be completed">
          {error}
        </Alert>
      ) : null}
      {factorMessage ? <Alert tone="info">{factorMessage}</Alert> : null}
      {notice ? <Alert tone="success">{notice}</Alert> : null}

      {next === "pin" ? (
        <Card>
          <CardHeader title="Enter the temporary PIN" description="The PIN is checked by the server and never logged." />
          <div className="space-y-3 p-5">
            <Input
              value={pin}
              onChange={(event) => setPin(event.target.value.replace(/\D/g, "").slice(0, 10))}
              inputMode="numeric"
              autoComplete="one-time-code"
              placeholder="6-digit PIN"
              className="text-center font-mono text-2xl tracking-[0.35em]"
              aria-label="Temporary attendance PIN"
              data-testid="pin-input"
            />
            <p className="text-[11px] text-muted">
              {attempt.pin_attempts > 0
                ? `Incorrect attempts so far: ${attempt.pin_attempts}. Too many will require teacher review.`
                : "Ask your teacher to show the current PIN if you cannot read it."}
            </p>
            <Button className="w-full" onClick={() => void submitPin()} loading={busy === "pin"} disabled={pin.length < 4} data-testid="verify-pin">
              Verify PIN
            </Button>
          </div>
        </Card>
      ) : null}

      {next === "gps" ? (
        <Card>
          <CardHeader title="Location evidence" description="Requested once, for this check-in only." />
          <div className="space-y-3 p-5">
            <p className="text-sm leading-relaxed text-[#475467]">
              AttendX asks your browser for one location fix to compare with the classroom geofence.
              Indoor GPS can be imprecise; a weak fix is recorded as evidence and may lead to teacher
              review rather than automatic rejection.
            </p>
            <Button className="w-full" onClick={() => void submitLocation()} loading={busy === "gps"} data-testid="share-location">
              <LocateFixed size={16} /> Share my location
            </Button>
            <button
              type="button"
              onClick={() => {
                setBusy("gps");
                void api(`/attendance/attempts/${attempt.id}/location`, {
                  method: "POST",
                  body: JSON.stringify({ unavailable: true, permission_denied: false }),
                })
                  .then((response) => {
                    const typed = response as LocationStepResponse;
                    applyAttempt(typed.attempt, typed.next_step);
                    setFactorMessage("Location marked unavailable. This is recorded, not treated as proof of cheating.");
                  })
                  .catch((caught) => setError(errorMessage(caught)))
                  .finally(() => setBusy(null));
              }}
              className="w-full text-xs font-medium text-muted hover:text-brand"
            >
              I cannot share location on this device
            </button>
          </div>
        </Card>
      ) : null}

      {next === "face" ? (
        <FactorStep
          kind="face"
          busy={busy === "face"}
          onSubmit={(file) => void submitFactor("face", file)}
          title="Face verification"
          description="Capture a still image for the configured verification provider. If no provider is configured, the honest result is unavailable and your attempt goes to teacher review."
        />
      ) : null}

      {next === "liveness" ? (
        <FactorStep
          kind="liveness"
          busy={busy === "liveness"}
          onSubmit={(file) => void submitFactor("liveness", file)}
          title="Liveness detection"
          description="Liveness is verified by a separate provider, not inferred from a simple animation. Unavailable providers are reported as such."
        />
      ) : null}

      {next === null ? (
        <Card>
          <CardHeader title="Ready for the server decision" description="All required steps are recorded." />
          <div className="space-y-3 p-5">
            <p className="text-sm leading-relaxed text-[#475467]">
              The backend will evaluate every factor against the session policy. Accepted attendance
              receives a unique reference; borderline or missing evidence is sent to teacher review.
            </p>
            <Button className="w-full" size="lg" onClick={() => void finalize()} loading={busy === "finalize"} data-testid="finalize-attendance">
              <ShieldCheck size={17} /> Finalize attendance
            </Button>
          </div>
        </Card>
      ) : null}

      <p className="px-1 text-center text-[10px] leading-relaxed text-muted">
        Attempt {attempt.reference}. Session closes at {formatDateTime(session.ends_at)}. The backend,
        not this page, decides attendance.
      </p>
    </div>
  );
}

function FactorStep({
  kind,
  busy,
  onSubmit,
  title,
  description,
}: {
  kind: "face" | "liveness";
  busy: boolean;
  onSubmit: (file: File | null) => void;
  title: string;
  description: string;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);

  return (
    <Card>
      <CardHeader title={title} description="Your image is sent only to the configured provider." />
      <div className="space-y-3 p-5">
        <p className="text-sm leading-relaxed text-[#475467]">{description}</p>
        <label className="block cursor-pointer rounded-xl border border-dashed border-line bg-[#FAFBFD] p-4 text-center">
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            capture="user"
            className="sr-only"
            onChange={(event) => {
              const selected = event.target.files?.[0] ?? null;
              setFile(selected);
              setPreview(selected ? URL.createObjectURL(selected) : null);
            }}
          />
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Selected verification capture" className="mx-auto max-h-48 rounded-lg" />
          ) : (
            <p className="text-xs text-muted">
              Tap to take a photo or choose an image. A capture is optional only if you accept a
              review outcome.
            </p>
          )}
        </label>
        <Button className="w-full" onClick={() => onSubmit(file)} loading={busy}>
          Submit {kind === "face" ? "face" : "liveness"} check
        </Button>
        <button
          type="button"
          onClick={() => onSubmit(null)}
          className="w-full text-xs font-medium text-muted hover:text-brand"
        >
          Continue without a capture
        </button>
      </div>
    </Card>
  );
}
