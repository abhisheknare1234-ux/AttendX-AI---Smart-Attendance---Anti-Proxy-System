"use client";

import Link from "next/link";
import { Building2, KeyRound, ShieldCheck, SlidersHorizontal } from "lucide-react";
import { Alert, Badge, Card, CardHeader, DefinitionRow, PageHeader, Skeleton } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import type { Health, PolicyOut } from "@/lib/types";

export default function AdminSettingsPage() {
  const health = useApiData<Health>("/health/ready");
  const policies = useApiData<PolicyOut[]>("/admin/policies");
  const defaultPolicy = (policies.data ?? []).find((policy) => policy.is_default) ?? policies.data?.[0];

  return (
    <div>
      <PageHeader
        eyebrow="Settings"
        title="Institutional configuration"
        description="This build keeps configuration explicit. Attendance rules live in the policy table; secrets live in the environment."
      />

      <div className="grid gap-5 lg:grid-cols-2">
        <Card>
          <CardHeader title="Institution" action={<Building2 size={16} className="text-muted" />} />
          <div className="px-5 py-2">
            <DefinitionRow label="Target institution" value="ZEAL College of Engineering & Research, Pune" />
            <DefinitionRow label="Deployment model" value="Institutional pilot" />
            <DefinitionRow
              label="Environment"
              value={health.data ? <Badge tone="neutral">{health.data.environment}</Badge> : "…"}
            />
            <DefinitionRow label="API version" value={health.data?.version ?? "…"} />
          </div>
          <p className="px-5 pb-4 text-[11px] leading-relaxed text-muted">
            Institutional records are never generated in production. Accounts and academic data must
            come from authorized administrators or validated CSV imports.
          </p>
        </Card>

        <Card>
          <CardHeader
            title="Attendance default policy"
            action={
              <Link href="/admin/policies" className="text-xs font-semibold text-brand hover:underline">
                Manage policies
              </Link>
            }
          />
          <div className="px-5 py-2">
            {policies.loading ? (
              <Skeleton className="my-3 h-32" />
            ) : defaultPolicy ? (
              <>
                <DefinitionRow label="Policy" value={defaultPolicy.name} />
                <DefinitionRow label="Attendance window" value={`${defaultPolicy.attendance_window_seconds} seconds`} />
                <DefinitionRow label="QR refresh" value={`${defaultPolicy.qr_refresh_seconds} seconds`} />
                <DefinitionRow
                  label="Required factors"
                  value={
                    [
                      defaultPolicy.require_pin ? "PIN" : null,
                      defaultPolicy.require_geofence ? "Location" : null,
                      defaultPolicy.require_face ? "Face" : null,
                      defaultPolicy.require_liveness ? "Liveness" : null,
                    ]
                      .filter(Boolean)
                      .join(", ") || "None"
                  }
                />
              </>
            ) : (
              <p className="py-3 text-sm text-muted">No database policy; built-in defaults apply.</p>
            )}
          </div>
        </Card>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-3">
        {[
          ["Verification services", "Configure face and liveness providers, or leave them honestly unavailable.", "/admin/verification", ShieldCheck],
          ["Attendance policies", "Change window, rotation, required factors and review behaviour.", "/admin/policies", SlidersHorizontal],
          ["Account security", "Change your password and review session protections.", "/account/password", KeyRound],
        ].map(([label, detail, href, Icon]) => {
          const Component = Icon as typeof ShieldCheck;
          return (
            <Link
              key={label as string}
              href={href as string}
              className="rounded-xl border border-line bg-white p-4 hover:border-brand/40 hover:bg-active"
            >
              <Component size={17} className="text-brand" />
              <p className="mt-2 text-sm font-semibold text-ink">{label as string}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted">{detail as string}</p>
            </Link>
          );
        })}
      </div>

      <div className="mt-5">
        <Alert tone="info" title="Secrets are not editable here">
          Database URLs, session secrets, QR signing keys and provider tokens are environment
          configuration. The API returns only whether a provider is configured, never its URL token.
        </Alert>
      </div>
    </div>
  );
}
