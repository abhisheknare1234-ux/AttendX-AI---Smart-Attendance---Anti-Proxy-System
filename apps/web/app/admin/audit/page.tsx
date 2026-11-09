"use client";

import { Search } from "lucide-react";
import { useState } from "react";
import {
  Card,
  CardHeader,
  EmptyState,
  Input,
  PageHeader,
  Skeleton,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime, titleCase } from "@/lib/api";
import type { AuditEvent } from "@/lib/types";

export default function AdminAuditPage() {
  const [action, setAction] = useState("");
  const path = action ? `/admin/audit-logs?limit=200&action=${encodeURIComponent(action)}` : "/admin/audit-logs?limit=200";
  const events = useApiData<AuditEvent[]>(path);

  return (
    <div>
      <PageHeader
        eyebrow="Audit"
        title="Administrative audit trail"
        description="Append-only records of provisioning, session lifecycle, reviews, corrections and exports."
      />
      <Card>
        <CardHeader
          title={`${events.data?.length ?? 0} recent events`}
          action={
            <div className="relative">
              <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-muted" />
              <Input
                value={action}
                onChange={(event) => setAction(event.target.value)}
                placeholder="Filter by action"
                className="h-9 w-52 pl-8 text-xs"
              />
            </div>
          }
        />
        {events.loading ? (
          <div className="p-4">
            <Skeleton className="h-60" />
          </div>
        ) : !events.data?.length ? (
          <EmptyState title="No audit events" description="Actions will appear here as the institution uses the system." />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Action</Th>
                  <Th>Entity</Th>
                  <Th>Actor</Th>
                  <Th>When</Th>
                  <Th>Details</Th>
                </tr>
              </thead>
              <tbody>
                {events.data.map((event) => (
                  <tr key={event.id}>
                    <Td className="font-medium text-ink">{titleCase(event.action)}</Td>
                    <Td className="text-xs text-muted">
                      {event.entity_type}
                      <span className="block font-mono text-[10px]">{event.entity_id?.slice(0, 8) ?? "—"}</span>
                    </Td>
                    <Td className="font-mono text-[10px] text-muted">
                      {event.actor_user_id?.slice(0, 8) ?? "system"}
                    </Td>
                    <Td className="whitespace-nowrap text-[11px] text-muted">{formatDateTime(event.created_at)}</Td>
                    <Td className="max-w-[260px] truncate font-mono text-[10px] text-muted">
                      {event.details ? JSON.stringify(event.details) : "—"}
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
