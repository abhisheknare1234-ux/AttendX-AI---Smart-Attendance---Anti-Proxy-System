"use client";

import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Building2,
  CheckCircle2,
  GraduationCap,
  ServerCog,
  ShieldAlert,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime, titleCase } from "@/lib/api";
import type {
  AuditEvent,
  ClassOut,
  Health,
  SecurityEvent,
  User,
} from "@/lib/types";
import {
  Alert,
  Badge,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Skeleton,
  StatCard,
  statusTone,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useAuth } from "@/components/auth-provider";

export default function AdminOverviewPage() {
  const { user } = useAuth();
  const users = useApiData<User[]>("/admin/users?limit=200");
  const classes = useApiData<ClassOut[]>("/admin/classes");
  const students = useApiData<User[]>("/admin/students?limit=300");
  const teachers = useApiData<User[]>("/admin/teachers");
  const audit = useApiData<AuditEvent[]>("/admin/audit-logs?limit=8");
  const security = useApiData<SecurityEvent[]>("/admin/security-events?limit=5");
  const health = useApiData<Health>("/health/ready");

  const loading = users.loading || classes.loading || students.loading || teachers.loading;
  const error = users.error || classes.error || students.error || teachers.error || health.error;

  return (
    <div>
      <PageHeader
        title={`Institutional overview`}
        description={`Signed in as ${user?.full_name ?? "administrator"}. All figures below are read directly from the database.`}
        eyebrow="Administrator"
        actions={
          <>
            <Link
              href="/admin/users"
              className="inline-flex h-10 items-center gap-2 rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-hover"
            >
              Provision accounts <ArrowRight size={15} />
            </Link>
            <Link
              href="/admin/reports"
              className="inline-flex h-10 items-center rounded-lg border border-line bg-white px-4 text-sm font-semibold text-ink hover:bg-active"
            >
              Attendance reports
            </Link>
          </>
        }
      />

      {error ? (
        <div className="mb-5">
          <Alert tone="danger" title="Some dashboard data could not be loaded">
            {error}
          </Alert>
        </div>
      ) : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28" />)
        ) : (
          <>
            <StatCard
              label="Students"
              value={students.data?.length ?? 0}
              hint="Provisioned student accounts"
              icon={<GraduationCap size={18} />}
            />
            <StatCard
              label="Teachers"
              value={teachers.data?.length ?? 0}
              hint="Authorized teaching accounts"
              icon={<UsersRound size={18} />}
              tone="purple"
            />
            <StatCard
              label="Classes"
              value={classes.data?.length ?? 0}
              hint="Active academic classes"
              icon={<Building2 size={18} />}
              tone="green"
            />
            <StatCard
              label="Verification services"
              value={
                health.data
                  ? `${health.data.face_provider === "none" ? "Face off" : "Face ready"} · ${
                      health.data.liveness_provider === "none" ? "Liveness off" : "Liveness ready"
                    }`
                  : "—"
              }
              hint="Providers must be configured institutionally"
              icon={<ServerCog size={18} />}
              tone={health.data?.face_provider === "none" ? "amber" : "green"}
            />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader
            title="Recent administrative activity"
            description="Append-only audit events recorded by the backend."
            action={
              <Link href="/admin/audit" className="text-xs font-semibold text-brand hover:underline">
                View audit logs
              </Link>
            }
          />
          {audit.loading ? (
            <div className="p-4">
              <Skeleton className="h-40" />
            </div>
          ) : audit.error ? (
            <div className="p-4">
              <Alert tone="danger">{audit.error}</Alert>
            </div>
          ) : !audit.data?.length ? (
            <EmptyState
              icon={<ShieldCheck size={20} />}
              title="No audit events yet"
              description="Provisioning, session lifecycle and review actions will appear here."
            />
          ) : (
            <TableWrap>
              <Table>
                <thead>
                  <tr>
                    <Th>Action</Th>
                    <Th>Entity</Th>
                    <Th>When</Th>
                  </tr>
                </thead>
                <tbody>
                  {audit.data.map((event) => (
                    <tr key={event.id}>
                      <Td>
                        <span className="font-medium text-ink">{titleCase(event.action)}</span>
                      </Td>
                      <Td>
                        <span className="text-muted">{event.entity_type}</span>
                      </Td>
                      <Td className="whitespace-nowrap text-muted">{formatDateTime(event.created_at)}</Td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </TableWrap>
          )}
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Security posture" description="Latest security events" />
            {security.loading ? (
              <div className="p-4">
                <Skeleton className="h-24" />
              </div>
            ) : !security.data?.length ? (
              <div className="px-5 py-8 text-center">
                <CheckCircle2 className="mx-auto text-[#12855A]" size={22} />
                <p className="mt-2 text-sm font-semibold text-ink">No security events recorded</p>
                <p className="mt-1 text-xs text-muted">Failed sign-ins and verification issues appear here.</p>
              </div>
            ) : (
              <ul className="divide-y divide-line">
                {security.data.map((event) => (
                  <li key={event.id} className="flex items-start justify-between gap-3 px-5 py-3">
                    <div>
                      <p className="text-xs font-semibold text-ink">{titleCase(event.event_type)}</p>
                      <p className="mt-0.5 text-[11px] text-muted">{formatDateTime(event.created_at)}</p>
                    </div>
                    <Badge tone={statusTone(event.severity)}>{event.severity}</Badge>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Quick configuration" />
            <div className="grid grid-cols-2 gap-2 p-4">
              {[
                ["Classes", "/admin/classes", BookOpen],
                ["Subjects", "/admin/subjects", BookOpen],
                ["Classrooms", "/admin/classrooms", Building2],
                ["Policies", "/admin/policies", ShieldAlert],
              ].map(([label, href, Icon]) => {
                const Component = Icon as typeof BookOpen;
                return (
                  <Link
                    key={label as string}
                    href={href as string}
                    className="flex items-center gap-2 rounded-lg border border-line px-3 py-2.5 text-xs font-semibold text-ink hover:border-brand/40 hover:bg-active"
                  >
                    <Component size={14} className="text-brand" /> {label as string}
                  </Link>
                );
              })}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
