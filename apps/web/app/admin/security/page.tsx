"use client";

import { ShieldAlert } from "lucide-react";
import { useState } from "react";
import {
  Badge,
  Card,
  CardHeader,
  EmptyState,
  PageHeader,
  Select,
  Skeleton,
  statusTone,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime, titleCase } from "@/lib/api";
import type { SecurityEvent } from "@/lib/types";

export default function AdminSecurityPage() {
  const [severity, setSeverity] = useState("");
  const path = severity
    ? `/admin/security-events?limit=200&severity=${severity}`
    : "/admin/security-events?limit=200";
  const events = useApiData<SecurityEvent[]>(path);

  return (
    <div>
      <PageHeader
        eyebrow="Security"
        title="Security events"
        description="Sign-in failures, lockouts, PIN failures and rejected attendance decisions. Secrets and PIN values are never written to this log."
      />
      <Card>
        <CardHeader
          title={`${events.data?.length ?? 0} events`}
          action={
            <Select value={severity} onChange={(event) => setSeverity(event.target.value)} className="h-9 w-40 text-xs">
              <option value="">All severities</option>
              <option value="info">Info</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </Select>
          }
        />
        {events.loading ? (
          <div className="p-4">
            <Skeleton className="h-56" />
          </div>
        ) : !events.data?.length ? (
          <EmptyState
            icon={<ShieldAlert size={22} />}
            title="No security events"
            description="No failed sign-ins, lockouts or verification failures are recorded."
          />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Event</Th>
                  <Th>Severity</Th>
                  <Th>User</Th>
                  <Th>IP</Th>
                  <Th>When</Th>
                  <Th>Details</Th>
                </tr>
              </thead>
              <tbody>
                {events.data.map((event) => (
                  <tr key={event.id}>
                    <Td className="font-medium text-ink">{titleCase(event.event_type)}</Td>
                    <Td>
                      <Badge tone={statusTone(event.severity)}>{titleCase(event.severity)}</Badge>
                    </Td>
                    <Td className="font-mono text-[10px] text-muted">{event.user_id?.slice(0, 8) ?? "—"}</Td>
                    <Td className="font-mono text-[10px] text-muted">{event.ip_address ?? "—"}</Td>
                    <Td className="whitespace-nowrap text-[11px] text-muted">{formatDateTime(event.created_at)}</Td>
                    <Td className="max-w-[240px] truncate font-mono text-[10px] text-muted">
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
