"use client";

import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Modal,
  PageHeader,
  Select,
  Skeleton,
  Table,
  TableWrap,
  Td,
  Th,
  statusTone,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage, formatDateTime } from "@/lib/api";
import type { AssignmentOut, ClassOut, SubjectOut, User } from "@/lib/types";

export default function AdminAssignmentsPage() {
  const assignments = useApiData<AssignmentOut[]>("/admin/assignments");
  const teachers = useApiData<User[]>("/admin/teachers");
  const classes = useApiData<ClassOut[]>("/admin/classes");
  const subjects = useApiData<SubjectOut[]>("/admin/subjects");
  const [open, setOpen] = useState(false);
  const [teacherId, setTeacherId] = useState("");
  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const classSubjects = (subjects.data ?? []).filter((item) => item.class_id === classId);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/admin/assignments", {
        method: "POST",
        body: JSON.stringify({ teacher_id: teacherId, class_id: classId, subject_id: subjectId || null }),
      });
      setOpen(false);
      setTeacherId("");
      setClassId("");
      setSubjectId("");
      await assignments.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function deactivate(id: string) {
    if (!window.confirm("Deactivate this teaching assignment? Existing sessions are unaffected, but new sessions will be blocked.")) return;
    try {
      await api(`/admin/assignments/${id}`, { method: "DELETE" });
      await assignments.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Academic configuration"
        title="Teacher assignments"
        description="A teacher can only create an attendance session for an active class/subject assignment."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Assign teacher
          </Button>
        }
      />
      {error ? (
        <div className="mb-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}
      <Card>
        <CardHeader title={`${assignments.data?.length ?? 0} assignments`} />
        {assignments.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : !assignments.data?.length ? (
          <p className="p-5 text-sm text-muted">No teaching assignments configured.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Teacher</Th>
                  <Th>Class</Th>
                  <Th>Subject</Th>
                  <Th>Status</Th>
                  <Th>Assigned</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {assignments.data.map((item) => (
                  <tr key={item.id}>
                    <Td className="font-medium text-ink">{item.teacher_name}</Td>
                    <Td className="text-xs text-muted">{item.class_name}</Td>
                    <Td className="text-xs text-muted">{item.subject_name ?? "All subjects"}</Td>
                    <Td>
                      <Badge tone={statusTone(item.is_active ? "active" : "disabled")}>
                        {item.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </Td>
                    <Td className="text-[11px] text-muted">{formatDateTime(item.assigned_at)}</Td>
                    <Td className="text-right">
                      {item.is_active ? (
                        <Button size="sm" variant="ghost" onClick={() => void deactivate(item.id)}>
                          Deactivate
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

      <Modal open={open} onClose={() => setOpen(false)} title="Assign a teacher" description="The backend validates that the subject belongs to the selected class.">
        <form onSubmit={submit} className="space-y-4">
          <Field label="Teacher" required>
            <Select value={teacherId} onChange={(event) => setTeacherId(event.target.value)} required>
              <option value="">Select a teacher</option>
              {(teachers.data ?? []).map((teacher) => (
                <option key={teacher.id} value={teacher.teacher?.id ?? ""}>
                  {teacher.full_name} ({teacher.teacher?.employee_id})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Class" required>
            <Select
              value={classId}
              onChange={(event) => {
                setClassId(event.target.value);
                setSubjectId("");
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
          <Field label="Subject" hint="Leave blank for an all-subjects assignment.">
            <Select value={subjectId} onChange={(event) => setSubjectId(event.target.value)} disabled={!classId}>
              <option value="">All subjects in this class</option>
              {classSubjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.name} ({subject.code})
                </option>
              ))}
            </Select>
          </Field>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy} disabled={!teacherId || !classId}>
              Create assignment
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
