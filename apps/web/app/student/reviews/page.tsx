"use client";

import Link from "next/link";
import { ListChecks } from "lucide-react";
import { Badge, Card, EmptyState, PageHeader, Skeleton, statusTone } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime, titleCase } from "@/lib/api";
import type { Review } from "@/lib/types";

export default function StudentReviewsPage() {
  const reviews = useApiData<Review[]>("/student/reviews");
  return (
    <div>
      <PageHeader
        eyebrow="Review requests"
        title="Your review requests"
        description="Teacher decisions on attendance cases that needed human review. Requests are created from a session record in your history."
      />
      {reviews.loading ? (
        <div className="space-y-3">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      ) : reviews.error ? (
        <p className="rounded-lg border border-[#FECDCA] bg-[#FFF5F4] px-4 py-3 text-sm text-[#912018]">
          {reviews.error}
        </p>
      ) : !reviews.data?.length ? (
        <Card>
          <EmptyState
            icon={<ListChecks size={22} />}
            title="No review requests"
            description="If you believe an attendance decision is wrong, open the record in your history and request a review with context."
            action={
              <Link href="/student/attendance" className="text-sm font-semibold text-brand hover:underline">
                Go to attendance history
              </Link>
            }
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {reviews.data.map((review) => (
            <Card key={review.id} className="p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-ink">{review.subject_name}</p>
                  <p className="text-[11px] text-muted">
                    {review.class_name} · {formatDateTime(review.session_starts_at)}
                  </p>
                </div>
                <Badge tone={statusTone(review.status)}>{titleCase(review.status)}</Badge>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-[#475467]">{review.reason}</p>
              {review.resolution_note ? (
                <p className="mt-2 rounded-lg bg-[#FAFBFD] px-3 py-2 text-xs text-[#475467]">
                  <span className="font-semibold text-ink">Teacher note:</span> {review.resolution_note}
                </p>
              ) : null}
              <p className="mt-2 text-[10px] text-muted">
                Requested {formatDateTime(review.created_at)}
                {review.resolved_at ? ` · resolved ${formatDateTime(review.resolved_at)}` : ""}
              </p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
