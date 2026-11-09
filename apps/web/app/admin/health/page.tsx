"use client";

import { Activity, Database, ServerCog } from "lucide-react";
import { Alert, Badge, Card, CardHeader, PageHeader, Skeleton, statusTone } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import type { Health } from "@/lib/types";

export default function AdminHealthPage() {
  const health = useApiData<Health>("/health/ready");
  return (
    <div>
      <PageHeader
        eyebrow="Operations"
        title="System health"
        description="Live readiness from the API process and its database connection."
      />
      {health.error ? <Alert tone="danger">{health.error}</Alert> : null}
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {health.loading || !health.data ? (
          Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-40" />)
        ) : (
          <>
            <Card>
              <CardHeader title="API" action={<Activity size={16} className="text-muted" />} />
              <div className="space-y-3 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Readiness</span>
                  <Badge tone={statusTone(health.data.status)}>{health.data.status}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Environment</span>
                  <Badge tone="neutral">{health.data.environment}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Version</span>
                  <span className="font-mono text-xs">{health.data.version}</span>
                </div>
              </div>
            </Card>
            <Card>
              <CardHeader title="Database" action={<Database size={16} className="text-muted" />} />
              <div className="space-y-3 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Connection</span>
                  <Badge tone={statusTone(health.data.database)}>{health.data.database}</Badge>
                </div>
                <p className="text-xs leading-relaxed text-muted">
                  Production uses PostgreSQL. The local development profile can use SQLite; both are
                  exercised by the same SQLAlchemy models and migrations.
                </p>
              </div>
            </Card>
            <Card>
              <CardHeader title="Providers" action={<ServerCog size={16} className="text-muted" />} />
              <div className="space-y-3 p-5">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Face</span>
                  <Badge tone={health.data.face_provider === "none" ? "amber" : "green"}>
                    {health.data.face_provider}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted">Liveness</span>
                  <Badge tone={health.data.liveness_provider === "none" ? "amber" : "green"}>
                    {health.data.liveness_provider}
                  </Badge>
                </div>
                <p className="text-xs leading-relaxed text-muted">
                  Provider outages are reported as UNAVAILABLE and routed to review rather than
                  silently failing a student.
                </p>
              </div>
            </Card>
          </>
        )}
      </div>

      <Card className="mt-5">
        <CardHeader title="Operational notes" />
        <ul className="grid gap-2 p-5 text-xs leading-relaxed text-muted sm:grid-cols-2">
          <li>• Health endpoints: <code>/api/v1/health/live</code> and <code>/api/v1/health/ready</code>.</li>
          <li>• Database migrations are applied with Alembic; the development profile creates tables on startup.</li>
          <li>• API logs exclude passwords, session tokens, PINs and raw biometric images.</li>
          <li>• Backups and retention must be configured by the deploying institution.</li>
        </ul>
      </Card>
    </div>
  );
}
