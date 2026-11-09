"use client";

import Link from "next/link";
import { KeyRound, UserRound } from "lucide-react";
import { Alert, Card, CardHeader, DefinitionRow, PageHeader, Skeleton } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime } from "@/lib/api";
import type { User } from "@/lib/types";

export default function TeacherProfilePage() {
  const profile = useApiData<User>("/teacher/profile");
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader eyebrow="Profile" title="Your teacher account" description="Account details are provisioned by an administrator." />
      {profile.error ? <Alert tone="danger">{profile.error}</Alert> : null}
      <div className="grid gap-5 sm:grid-cols-2">
        <Card>
          <CardHeader title="Identity" action={<UserRound size={16} className="text-muted" />} />
          <div className="px-5 py-2">
            {profile.loading || !profile.data ? (
              <Skeleton className="my-3 h-32" />
            ) : (
              <>
                <DefinitionRow label="Full name" value={profile.data.full_name} />
                <DefinitionRow label="Email" value={profile.data.email} />
                <DefinitionRow label="Role" value="Teacher" />
                <DefinitionRow label="Status" value={profile.data.status} />
              </>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Employment" />
          <div className="px-5 py-2">
            {profile.loading || !profile.data ? (
              <Skeleton className="my-3 h-32" />
            ) : (
              <>
                <DefinitionRow label="Employee ID" value={profile.data.teacher?.employee_id ?? "—"} />
                <DefinitionRow label="Department" value={profile.data.teacher?.department ?? "—"} />
                <DefinitionRow label="Designation" value={profile.data.teacher?.designation ?? "—"} />
                <DefinitionRow label="Last sign-in" value={formatDateTime(profile.data.last_login_at)} />
              </>
            )}
          </div>
        </Card>
      </div>
      <Card className="mt-5">
        <div className="flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-sm font-semibold text-ink">Account security</p>
            <p className="mt-0.5 text-xs text-muted">
              Change your password. Sessions are server-managed and CSRF-protected.
            </p>
          </div>
          <Link
            href="/account/password"
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-line px-4 text-sm font-semibold text-ink hover:bg-active"
          >
            <KeyRound size={15} /> Change password
          </Link>
        </div>
      </Card>
    </div>
  );
}
