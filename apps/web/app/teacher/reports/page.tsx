"use client";

import { Download } from "lucide-react";
import { useMemo, useState } from "react";
import {
  Button,
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
import type { ReportResponse, SubjectOut } from "@/lib/types";

interface ClassRow {
  id: string;
  code: string;
  name: string;
}

export default function TeacherReportsPage() {
  const classes = useApiData<ClassRow[]>("/teacher/classes");
  const [classId, setClassId] = useState("");
  const subjects = useApiData<SubjectOut[]>(classId ? `/subjects?class_id=${classId}` : "/subjects");
  const [subjectId, setSubjectId] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (classId) params.set("class_id", classId);
    if (subjectId) params.set("subject_id", subjectId);
    if (fromDate) params.set("from", fromDate);
    if (toDate) params.set("to", toDate);
    const value = params.toString();
    return value ? `?${value}` : "";
  }, [classId, subjectId, fromDate, toDate]);

  const report = useApiData<ReportResponse>(`/reports/attendance${query}`);

  return (
    <div>
      <PageHeader
        eyebrow="Reports"
        title="Attendance reports"
        description="Computed from held sessions and recorded attendance. Teachers can only report on their assigned classes."
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
        <CardHeader title="Filters" description="All filters are applied server-side." />
        <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Class">
            <Select
              value={classId}
              onChange={(event) => {
                setClassId(event.target.value);
                setSubjectId("");
              }}
            >
              <option value="">All assigned classes</option>
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
              {(subjects.data ?? []).map((item) => (
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
        <Summary label="Students" value={report.data?.totals.students ?? "—"} />
        <Summary label="Sessions held" value={report.data?.totals.sessions ?? "—"} />
        <Summary label="Present records" value={report.data?.totals.present ?? "—"} />
        <Summary
          label="Average attendance"
          value={
            report.data?.totals.average_percentage !== undefined &&
            report.data?.totals.average_percentage !== null
              ? `${report.data.totals.average_percentage}%`
              : "—"
          }
        />
      </div>

      <Card>
        <CardHeader
          title="Student attendance"
          description={
            report.data
              ? `Generated ${formatDateTime(report.data.generated_at)}`
              : "Calculated from the shared attendance records."
          }
        />
        {report.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : report.error ? (
          <div className="p-5 text-sm text-[#912018]">{report.error}</div>
        ) : !report.data?.rows.length ? (
          <EmptyState
            title="No report rows"
            description="No held sessions or enrolments match the selected filters yet."
          />
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
                    <Td className="text-muted">{row.class_name}</Td>
                    <Td className="text-muted">{row.subject_name}</Td>
                    <Td className="text-muted">{row.sessions_held}</Td>
                    <Td className="text-muted">{row.sessions_present}</Td>
                    <Td>
                      <span
                        className={
                          row.attendance_percentage !== null && row.attendance_percentage < 75
                            ? "font-semibold text-[#B42318]"
                            : "font-semibold text-ink"
                        }
                      >
                        {row.attendance_percentage === null ? "No sessions" : `${row.attendance_percentage}%`}
                      </span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <p className="mt-4 text-xs text-muted">
        Percentage = present records / held sessions for the selected scope. Sessions still open are
        included only after they have started. Review-required records are not counted as present
        until a teacher resolves them.
      </p>
    </div>
  );
}

function Summary({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-line bg-white p-4">
      <p className="text-[11px] font-medium text-muted">{label}</p>
      <p className="mt-1 text-xl font-semibold text-ink">{value}</p>
    </div>
  );
}
