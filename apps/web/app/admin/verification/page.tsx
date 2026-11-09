"use client";

import { CheckCircle2, ServerCog, XCircle } from "lucide-react";
import { Alert, Badge, Card, CardHeader, PageHeader, Skeleton, statusTone } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import type { Health } from "@/lib/types";

export default function AdminVerificationPage() {
  const health = useApiData<Health>("/health/ready");

  return (
    <div>
      <PageHeader
        eyebrow="Verification services"
        title="Identity provider status"
        description="Face and liveness are external contracts. This build never fabricates a successful verification or a confidence score."
      />

      {health.error ? <Alert tone="danger">{health.error}</Alert> : null}

      <div className="grid gap-5 lg:grid-cols-2">
        {health.loading || !health.data ? (
          <>
            <Skeleton className="h-52" />
            <Skeleton className="h-52" />
          </>
        ) : (
          <>
            <Card>
              <CardHeader
                title="Face verification provider"
                action={<ServerCog size={16} className="text-muted" />}
              />
              <div className="space-y-4 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Configured provider</span>
                  <Badge tone={health.data.face_provider === "none" ? "amber" : "green"}>
                    {health.data.face_provider === "none" ? "Not configured" : health.data.face_provider}
                  </Badge>
                </div>
                <div className="rounded-lg border border-line bg-[#FAFBFD] p-4 text-xs leading-relaxed text-[#475467]">
                  {health.data.face_provider === "none" ? (
                    <p className="flex items-start gap-2">
                      <XCircle size={15} className="mt-0.5 shrink-0 text-[#B42318]" />
                      No face provider is configured. Sessions that require face verification will
                      record an honest <strong>UNAVAILABLE</strong> state and route affected attempts
                      to teacher review. No match or score is invented.
                    </p>
                  ) : (
                    <p className="flex items-start gap-2">
                      <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-[#12855A]" />
                      An external face provider is configured. The backend calls it with the
                      student&apos;s enrollment reference and one capture, and stores the returned
                      status, score, provider and model version.
                    </p>
                  )}
                </div>
                <div className="text-xs text-muted">
                  Configure through <code className="rounded bg-workspace px-1">FACE_PROVIDER</code>,{" "}
                  <code className="rounded bg-workspace px-1">FACE_HTTP_URL</code> and{" "}
                  <code className="rounded bg-workspace px-1">FACE_HTTP_TOKEN</code>. Secrets are read
                  from the environment and never returned by the API.
                </div>
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Liveness detection provider"
                action={<ServerCog size={16} className="text-muted" />}
              />
              <div className="space-y-4 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Configured provider</span>
                  <Badge tone={health.data.liveness_provider === "none" ? "amber" : "green"}>
                    {health.data.liveness_provider === "none" ? "Not configured" : health.data.liveness_provider}
                  </Badge>
                </div>
                <div className="rounded-lg border border-line bg-[#FAFBFD] p-4 text-xs leading-relaxed text-[#475467]">
                  {health.data.liveness_provider === "none" ? (
                    <p className="flex items-start gap-2">
                      <XCircle size={15} className="mt-0.5 shrink-0 text-[#B42318]" />
                      No liveness provider is configured. Liveness is reported as{" "}
                      <strong>UNAVAILABLE</strong> rather than simulated. Simple blink or head-turn
                      prompts are not claimed to defeat replay attacks.
                    </p>
                  ) : (
                    <p className="flex items-start gap-2">
                      <CheckCircle2 size={15} className="mt-0.5 shrink-0 text-[#12855A]" />
                      {health.data.liveness_provider === "local_minifas"
                        ? "Local MiniFASNet single-frame anti-spoofing is configured. It detects print/screen-like texture, but it is not a challenge-response protocol and does not prove a live person is present."
                        : "An external liveness provider is configured. Its PASSED/FAILED result is recorded separately from face matching."}
                    </p>
                  )}
                </div>
                <div className="text-xs text-muted">
                  Configure through <code className="rounded bg-workspace px-1">LIVENESS_PROVIDER</code>{" "}
                  (<code>none</code>, <code>http</code> or <code>local_minifas</code>),{" "}
                  <code className="rounded bg-workspace px-1">LIVENESS_MODEL_DIR</code> or the HTTP
                  URL/token variables.
                </div>
              </div>
            </Card>
          </>
        )}
      </div>

      <Card className="mt-5">
        <CardHeader title="Runtime health" description="Readiness also checks database connectivity." />
        <div className="space-y-2 p-5 text-sm">
          {health.data ? (
            <>
              <div className="flex items-center justify-between">
                <span className="text-muted">Overall status</span>
                <Badge tone={statusTone(health.data.status)}>{health.data.status}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">Database</span>
                <Badge tone={statusTone(health.data.database)}>{health.data.database}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">Environment</span>
                <Badge tone="neutral">{health.data.environment}</Badge>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-muted">API version</span>
                <span className="font-mono text-xs">{health.data.version}</span>
              </div>
            </>
          ) : (
            <Skeleton className="h-24" />
          )}
        </div>
      </Card>

      <Alert tone="info" title="Privacy boundary">
        Administrators can see provider status only. Biometric templates, images and provider account
        credentials are not exposed through this interface. Access to verification evidence is limited
        to the teacher reviewing that session.
      </Alert>
    </div>
  );
}
