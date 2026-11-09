"use client";

import { Camera, CheckCircle2, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Skeleton,
  statusTone,
} from "@/components/ui";
import { api, errorMessage, formatDateTime, titleCase } from "@/lib/api";
import type { FaceEnrollment } from "@/lib/types";

export function FaceEnrollmentCard() {
  const [data, setData] = useState<FaceEnrollment | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef<HTMLInputElement | null>(null);

  async function load() {
    setLoading(true);
    try {
      setData(await api<FaceEnrollment>("/student/face-enrollment"));
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function enroll() {
    if (!file || !consent) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const form = new FormData();
      form.append("image", file);
      form.append("consent", "true");
      form.append("consent_version", "pilot-v1");
      const result = await api<FaceEnrollment>("/student/face-enrollment", {
        method: "POST",
        body: form,
      });
      setData(result);
      setFile(null);
      setConsent(false);
      setMessage("Face template encrypted and enrolled. The reference image was not stored.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Delete your face enrollment? Verification requiring face will no longer be possible until you re-enroll.")) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setData(await api<FaceEnrollment>("/student/face-enrollment", { method: "DELETE" }));
      setMessage("Face template deleted.");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Face verification enrollment"
        description="Optional, consent-based enrollment for attendance factors that require face verification."
        action={<ShieldCheck size={16} className="text-muted" />}
      />
      <div className="space-y-3 p-4">
        {loading ? (
          <Skeleton className="h-20" />
        ) : data ? (
          <>
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs text-muted">Enrollment status</p>
                <p className="mt-0.5">
                  <Badge tone={statusTone(data.status.replace("not_enrolled", "pending"))}>
                    {titleCase(data.status)}
                  </Badge>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted">Provider</p>
                <p className="text-sm font-medium text-ink">{data.provider}</p>
              </div>
            </div>

            {data.status === "active" ? (
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2 rounded-lg bg-[#FAFBFD] p-3 text-[11px]">
                  <p>
                    <span className="block text-[10px] uppercase tracking-wide text-muted">Model</span>
                    {data.model_name ?? "—"} {data.model_version ? `(${data.model_version})` : ""}
                  </p>
                  <p>
                    <span className="block text-[10px] uppercase tracking-wide text-muted">Dimension</span>
                    {data.dimension ?? "—"}
                  </p>
                  <p>
                    <span className="block text-[10px] uppercase tracking-wide text-muted">Consent</span>
                    {data.consent_version ?? "—"} · {formatDateTime(data.consented_at)}
                  </p>
                  <p>
                    <span className="block text-[10px] uppercase tracking-wide text-muted">Stored</span>
                    Encrypted template only
                  </p>
                </div>
                <Button variant="secondary" onClick={() => void remove()} loading={busy}>
                  <Trash2 size={14} /> Delete face enrollment
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {!data.local_face_available && data.provider === "local_opencv" ? (
                  <Alert tone="warning" title="Local face models are not installed">
                    An administrator must install the YuNet/SFace models before enrollment can be
                    used. No face verification will be fabricated without them.
                  </Alert>
                ) : null}
                <label className="block cursor-pointer rounded-xl border border-dashed border-line bg-[#FAFBFD] p-4 text-center">
                  <input
                    ref={inputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    capture="user"
                    className="sr-only"
                    onChange={(event) => setFile(event.target.files?.[0] ?? null)}
                  />
                  <span className="mx-auto flex h-9 w-9 items-center justify-center rounded-full bg-active text-brand">
                    <Camera size={17} />
                  </span>
                  <span className="mt-2 block text-xs font-medium text-ink">
                    {file ? file.name : "Take or choose a front-facing photo"}
                  </span>
                  <span className="mt-0.5 block text-[10px] text-muted">
                    Exactly one face · JPEG/PNG/WebP · under 5 MB
                  </span>
                </label>
                <label className="flex items-start gap-2 text-[11px] leading-relaxed text-[#475467]">
                  <input
                    type="checkbox"
                    checked={consent}
                    onChange={(event) => setConsent(event.target.checked)}
                    className="mt-0.5 h-4 w-4 rounded border-line"
                  />
                  <span>
                    I consent to the creation of a face template for attendance verification under
                    my institution&apos;s policy (consent version <code>pilot-v1</code>). I understand
                    the reference image is not stored and I can delete the template at any time.
                  </span>
                </label>
                <Button
                  className="w-full"
                  onClick={() => void enroll()}
                  loading={busy}
                  disabled={!file || !consent}
                >
                  <ShieldCheck size={15} /> Encrypt and enroll face template
                </Button>
              </div>
            )}

            {message ? <Alert tone="success">{message}</Alert> : null}
            <p className="text-[10px] leading-relaxed text-muted">
              Face matching is not liveness detection. A configured liveness provider (
              {data.liveness_provider === "none" ? "none" : data.liveness_provider}) is required
              separately for presentation/replay resistance. The template is encrypted at rest and
              is never shown to administrators.
            </p>
          </>
        ) : null}
        {error ? <Alert tone="danger">{error}</Alert> : null}
        {data?.status === "active" ? (
          <p className="flex items-center gap-1 text-[10px] text-[#12855A]">
            <CheckCircle2 size={12} /> Active template available for face-required sessions.
          </p>
        ) : null}
      </div>
    </Card>
  );
}
