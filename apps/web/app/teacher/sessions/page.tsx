"use client";

import Link from "next/link";
import { ArrowRight, CalendarClock, PlayCircle } from "lucide-react";
import { Button, Card, EmptyState, PageHeader, Skeleton, Badge, statusTone, Table, TableWrap, Td, Th } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime, titleCase } from "@/lib/api";
import type { SessionOut } from "@/lib/types";

export default function TeacherSessionsPage() {
  const sessions = useApiData<SessionOut[]>("/teacher/sessions?limit=100");

  return (
    <div>
      <PageHeader
        eyebrow="Attendance sessions"
        title="Your attendance sessions"
        description="Scheduled, live and closed sessions you created. Counts come from attendance attempts and records."
        actions={
          <Link href="/teacher/sessions/new">
            <Button>
              <PlayCircle size={15} /> Start attendance
            </Button>
          </Link>
        }
      />

      {sessions.error ? (
        <p className="mb-4 rounded-lg border border-[#FECDCA] bg-[#FFF5F4] px-4 py-3 text-sm text-[#912018]">
          {sessions.error}
        </p>
      ) : null}

      <Card>
        {sessions.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : !sessions.data?.length ? (
          <EmptyState
            icon={<CalendarClock size={20} />}
            title="No sessions yet"
            description="Create a session for an assigned class. You can open the check-in window when you are ready."
            action={
              <Link href="/teacher/sessions/new">
                <Button size="sm">Create a session</Button>
              </Link>
            }
          />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Subject / class</Th>
                  <Th>When</Th>
                  <Th>Status</Th>
                  <Th>Verified</Th>
                  <Th>Review</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {sessions.data.map((session) => (
                  <tr key={session.id}>
                    <Td>
                      <p className="font-medium text-ink">{session.subject_name}</p>
                      <p className="text-[11px] text-muted">
                        {session.class_name} · {session.classroom_name}
                      </p>
                    </Td>
                    <Td className="whitespace-nowrap text-xs text-muted">
                      {formatDateTime(session.starts_at)}
                      <span className="block">ends {formatDateTime(session.ends_at)}</span>
                    </Td>
                    <Td>
                      <Badge tone={statusTone(session.status)}>{titleCase(session.status)}</Badge>
                    </Td>
                    <Td>
                      <span className="font-semibold text-ink">{session.accepted}</span>
                      <span className="text-muted"> / {session.eligible_students}</span>
                    </Td>
                    <Td>
                      {session.review_required ? (
                        <Badge tone="amber">{session.review_required} pending</Badge>
                      ) : (
                        <span className="text-xs text-muted">None</span>
                      )}
                    </Td>
                    <Td className="text-right">
                      <Link
                        href={`/teacher/sessions/${session.id}`}
                        className="inline-flex items-center gap-1 text-xs font-semibold text-brand hover:underline"
                      >
                        {session.status === "open" ? "Monitor" : "Open"} <ArrowRight size={12} />
                      </Link>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>
    </div>
  );
}
