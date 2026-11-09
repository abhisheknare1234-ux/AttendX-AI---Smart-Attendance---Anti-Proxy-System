"use client";

import { Download } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Card,
  CardHeader,
  EmptyState,
  Field,
  Input,
  PageHeader,
  Select,
  Skeleton,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { formatDateTime } from "@/lib/api";
import type { ClassOut, ReportResponse, SubjectOut } from "@/lib/types";

export default function AdminReportsPage() {
  const classes = useApiData<ClassOut[]>("/admin/classes");
  const [classId, setClassId] = useState("");
  const subjects = useApiData<SubjectOut[]>(classId ? `/admin/subjects?class_id=${classId}` : "/admin/subjects");
  const [subjectId, setSubjectId] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (classId) params.set("class_id", classId);
    if (subjectId) params.set("subject_id", subjectId);
    if (fromDate) params.set("from", fromDate);
    if (toDate) params.set("to", toDate);
    return params.toString() ? `?${params.toString()}` : "";
  }, [classId, subjectId, fromDate, toDate]);

  const report = useApiData<ReportResponse>(`/reports/attendance${query}`);

  return (
    <div>
      <PageHeader
        eyebrow="Reports"
        title="Attendance reports"
        description="Authoritative percentages computed from held sessions and attendance records."
        actions={
          <a
            href={`/api/v1/reports/export${query}`}
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-line bg-white px-4 text-sm font-semibold text-ink hover:bg-active"
          >
            <Download size={15} /> Export CSV
          </a>
        }
      />
      <Card className="mb-5">
        <CardHeader title="Filters" />
        <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Class">
            <Select
              value={classId}
              onChange={(event) => {
                setClassId(event.target.value);
                setSubjectId("");
              }}
            >
              <option value="">All classes</option>
              {(classes.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.code})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Subject">
            <Select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
              <option value="">All subjects</option>
              {(subjects.data ?? [])
                .filter((item) => !classId || item.class_id === classId)
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
            </Select>
          </Field>
          <Field label="From">
            <Input type="date" value={fromDate} onChange={(event) => setFromDate(event.target.value)} />
          </Field>
          <Field label="To">
            <Input type="date" value={toDate} onChange={(event) => setToDate(event.target.value)} />
          </Field>
        </div>
      </Card>

      <div className="mb-4 grid gap-3 sm:grid-cols-4">
        {[
          ["Students", report.data?.totals.students],
          ["Sessions held", report.data?.totals.sessions],
          ["Present records", report.data?.totals.present],
          [
            "Average",
            report.data?.totals.average_percentage === null || report.data?.totals.average_percentage === undefined
              ? "—"
              : `${report.data.totals.average_percentage}%`,
          ],
        ].map(([label, value]) => (
          <div key={String(label)} className="rounded-xl border border-line bg-white p-4">
            <p className="text-[11px] text-muted">{label}</p>
            <p className="mt-1 text-xl font-semibold text-ink">{value ?? "—"}</p>
          </div>
        ))}
      </div>

      <Card>
        <CardHeader
          title="Student attendance rows"
          description={report.data ? `Generated ${formatDateTime(report.data.generated_at)}` : "—"}
        />
        {report.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : report.error ? (
          <p className="p-5 text-sm text-[#912018]">{report.error}</p>
        ) : !report.data?.rows.length ? (
          <EmptyState title="No rows" description="No sessions or enrolments match these filters." />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Student</Th>
                  <Th>Class</Th>
                  <Th>Subject</Th>
                  <Th>Held</Th>
                  <Th>Present</Th>
                  <Th>Attendance</Th>
                </tr>
              </thead>
              <tbody>
                {report.data.rows.map((row) => (
                  <tr key={`${row.student_id}-${row.subject_name}`}>
                    <Td>
                      <p className="font-medium text-ink">{row.student_name}</p>
                      <p className="text-[11px] text-muted">{row.roll_number}</p>
                    </Td>
                    <Td className="text-xs text-muted">{row.class_name}</Td>
                    <Td className="text-xs text-muted">{row.subject_name}</Td>
                    <Td className="text-xs text-muted">{row.sessions_held}</Td>
                    <Td className="text-xs text-muted">{row.sessions_present}</Td>
                    <Td className="font-semibold text-ink">
                      {row.attendance_percentage === null ? "No sessions" : `${row.attendance_percentage}%`}
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
