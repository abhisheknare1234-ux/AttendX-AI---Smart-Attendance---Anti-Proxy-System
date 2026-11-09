"use client";

import Link from "next/link";
import { KeyRound, UserRound } from "lucide-react";
import { Alert, Card, CardHeader, DefinitionRow, PageHeader, Skeleton } from "@/components/ui";
import { FaceEnrollmentCard } from "@/components/face-enrollment";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime } from "@/lib/api";
import type { User } from "@/lib/types";

export default function StudentProfilePage() {
  const profile = useApiData<User>("/student/profile");
  return (
    <div>
      <PageHeader eyebrow="Profile" title="Your student account" description="Provisioned by your institution. Contact an administrator for corrections." />
      {profile.error ? <Alert tone="danger">{profile.error}</Alert> : null}
      <div className="space-y-3">
        <Card>
          <CardHeader title="Account" action={<UserRound size={16} className="text-muted" />} />
          <div className="px-5 py-2">
            {profile.loading || !profile.data ? (
              <Skeleton className="my-3 h-28" />
            ) : (
              <>
                <DefinitionRow label="Name" value={profile.data.full_name} />
                <DefinitionRow label="Email" value={profile.data.email} />
                <DefinitionRow label="Status" value={profile.data.status} />
                <DefinitionRow label="Last sign-in" value={formatDateTime(profile.data.last_login_at)} />
              </>
            )}
          </div>
        </Card>
        <Card>
          <CardHeader title="Academic details" />
          <div className="px-5 py-2">
            {profile.loading || !profile.data ? (
              <Skeleton className="my-3 h-28" />
            ) : (
              <>
                <DefinitionRow label="Roll number" value={profile.data.student?.roll_number ?? "—"} />
                <DefinitionRow label="Programme" value={profile.data.student?.programme ?? "—"} />
                <DefinitionRow label="Department" value={profile.data.student?.department ?? "—"} />
                <DefinitionRow
                  label="Year / division"
                  value={
                    profile.data.student
                      ? `${profile.data.student.year} / ${profile.data.student.division}`
                      : "—"
                  }
                />
                <DefinitionRow label="Batch" value={profile.data.student?.batch ?? "—"} />
              </>
            )}
          </div>
        </Card>
      </div>
      <div className="mt-3">
        <FaceEnrollmentCard />
      </div>
      <Card className="mt-3">
        <div className="flex flex-wrap items-center justify-between gap-3 p-4">
          <div>
            <p className="text-sm font-semibold text-ink">Account security</p>
            <p className="text-xs text-muted">Change your password and review session security.</p>
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
