"use client";

import Link from "next/link";
import { BookOpen } from "lucide-react";
import { Card, CardHeader, EmptyState, PageHeader, Skeleton } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import type { SubjectSummary } from "@/lib/types";

export default function StudentSubjectsPage() {
  const subjects = useApiData<SubjectSummary[]>("/student/subjects");

  return (
    <div>
      <PageHeader
        eyebrow="Subjects"
        title="Subject-wise attendance"
        description="Held sessions and present records across the classes you are enrolled in."
      />
      {subjects.loading ? (
        <div className="space-y-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : subjects.error ? (
        <p className="rounded-lg border border-[#FECDCA] bg-[#FFF5F4] px-4 py-3 text-sm text-[#912018]">
          {subjects.error}
        </p>
      ) : !subjects.data?.length ? (
        <Card>
          <EmptyState
            icon={<BookOpen size={22} />}
            title="No subjects yet"
            description="You will see subjects after an administrator enrols you in a class and the class has active subjects."
            action={
              <Link href="/student" className="text-sm font-semibold text-brand hover:underline">
                Back to home
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {subjects.data.map((subject) => (
            <Card key={subject.subject_id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-ink">{subject.subject_name}</p>
                  <p className="text-[11px] text-muted">
                    {subject.subject_code} · {subject.class_name}
                  </p>
                </div>
                <p className="text-lg font-semibold text-ink">
                  {subject.percentage === null ? "—" : `${subject.percentage}%`}
                </p>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-[#EDF1F7]">
                <div
                  className="h-full rounded-full bg-brand"
                  style={{ width: `${Math.min(100, subject.percentage ?? 0)}%` }}
                />
              </div>
              <p className="mt-2 text-[11px] text-muted">
                {subject.present} present of {subject.sessions} held sessions
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
