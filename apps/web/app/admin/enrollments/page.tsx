"use client";

import { Plus } from "lucide-react";
import { useMemo, useState, type FormEvent } from "react";
import {
  Alert,
  Button,
  Card,
  CardHeader,
  Field,
  Modal,
  PageHeader,
  Select,
  Skeleton,
  statusTone,
  Badge,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage, formatDateTime, titleCase } from "@/lib/api";
import type { ClassOut, EnrollmentOut, User } from "@/lib/types";

export default function AdminEnrollmentsPage() {
  const enrollments = useApiData<EnrollmentOut[]>("/admin/enrollments");
  const classes = useApiData<ClassOut[]>("/admin/classes");
  const students = useApiData<User[]>("/admin/students?limit=300");
  const [open, setOpen] = useState(false);
  const [classId, setClassId] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const enrolledIds = useMemo(
    () =>
      new Set(
        (enrollments.data ?? [])
          .filter((item) => item.class_id === classId && item.status === "active")
          .map((item) => item.student_id),
      ),
    [enrollments.data, classId],
  );

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ created: number; skipped: number }>("/admin/enrollments", {
        method: "POST",
        body: JSON.stringify({ class_id: classId, student_ids: selected }),
      });
      setMessage(`${result.created} enrolment(s) created, ${result.skipped} already enrolled.`);
      setOpen(false);
      setSelected([]);
      await enrollments.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function drop(enrollmentId: string) {
    if (!window.confirm("Drop this enrolment? The student will no longer be eligible for sessions in this class.")) return;
    try {
      await api(`/admin/enrollments/${enrollmentId}`, { method: "DELETE" });
      await enrollments.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Academic configuration"
        title="Class enrolments"
        description="Only actively enrolled students are eligible to check in to a class session."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Enrol students
          </Button>
        }
      />
      {message ? (
        <div className="mb-4">
          <Alert tone="success">{message}</Alert>
        </div>
      ) : null}
      {error ? (
        <div className="mb-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}
      <Card>
        <CardHeader title={`${enrollments.data?.length ?? 0} enrolment records`} />
        {enrollments.loading ? (
          <div className="p-4">
            <Skeleton className="h-56" />
          </div>
        ) : !enrollments.data?.length ? (
          <p className="p-5 text-sm text-muted">No enrolments yet.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Student</Th>
                  <Th>Class</Th>
                  <Th>Status</Th>
                  <Th>Enrolled</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {enrollments.data.map((item) => (
                  <tr key={item.id}>
                    <Td>
                      <p className="font-medium text-ink">{item.student_name}</p>
                      <p className="text-[11px] text-muted">{item.roll_number}</p>
                    </Td>
                    <Td className="text-xs text-muted">{item.class_name}</Td>
                    <Td>
                      <Badge tone={statusTone(item.status)}>{titleCase(item.status)}</Badge>
                    </Td>
                    <Td className="text-[11px] text-muted">{formatDateTime(item.enrolled_at)}</Td>
                    <Td className="text-right">
                      {item.status === "active" ? (
                        <Button size="sm" variant="ghost" onClick={() => void drop(item.id)}>
                          Drop
                        </Button>
                      ) : null}
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Enrol students in a class" description="Already-enrolled students are skipped safely." size="md">
        <form onSubmit={submit} className="space-y-4">
          <Field label="Class" required>
            <Select
              value={classId}
              onChange={(event) => {
                setClassId(event.target.value);
                setSelected([]);
              }}
              required
            >
              <option value="">Select a class</option>
              {(classes.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.code})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Students" hint="Hold Ctrl/Cmd to select multiple. Enrolled students are marked.">
            <select
              multiple
              value={selected}
              onChange={(event) =>
                setSelected(Array.from(event.target.selectedOptions, (option) => option.value))
              }
              className="h-56 w-full rounded-lg border border-line bg-white px-2 py-2 text-sm"
            >
              {(students.data ?? []).map((student) => (
                <option key={student.id} value={student.id}>
                  {student.full_name} · {student.student?.roll_number}
                  {enrolledIds.has(student.id) ? " (enrolled)" : ""}
                </option>
              ))}
            </select>
          </Field>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy} disabled={!classId || !selected.length}>
              Enrol selected
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
