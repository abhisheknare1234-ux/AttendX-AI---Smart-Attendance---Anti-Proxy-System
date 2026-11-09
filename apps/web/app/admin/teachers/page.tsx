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
  Input,
  Modal,
  PageHeader,
  Skeleton,
  Table,
  TableWrap,
  Td,
  Th,
  statusTone,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage, titleCase } from "@/lib/api";
import type { User } from "@/lib/types";

export default function AdminTeachersPage() {
  const teachers = useApiData<User[]>("/admin/teachers");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    employee_id: "",
    department: "Computer Engineering",
    designation: "Assistant Professor",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [temp, setTemp] = useState<{ email: string; password: string } | null>(null);

  function set(key: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ user: User; temporary_password: string | null }>("/admin/teachers", {
        method: "POST",
        body: JSON.stringify({ ...form, password: form.password || null }),
      });
      if (result.temporary_password) setTemp({ email: result.user.email, password: result.temporary_password });
      setOpen(false);
      setForm((current) => ({ ...current, email: "", full_name: "", password: "", employee_id: "" }));
      await teachers.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Teachers"
        title="Teaching accounts"
        description="Teacher access is scoped to assigned classes and sessions. Assignments are configured separately."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Add teacher
          </Button>
        }
      />

      {temp ? (
        <div className="mb-4">
          <Alert tone="warning" title="Temporary password shown once">
            {temp.email} · <code className="font-mono">{temp.password}</code>
            <button type="button" onClick={() => setTemp(null)} className="ml-2 font-semibold underline">
              Dismiss
            </button>
          </Alert>
        </div>
      ) : null}

      <Card>
        <CardHeader title={`${teachers.data?.length ?? 0} teacher account(s)`} />
        {teachers.loading ? (
          <div className="p-4">
            <Skeleton className="h-48" />
          </div>
        ) : !teachers.data?.length ? (
          <p className="p-5 text-sm text-muted">No teacher accounts yet.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Teacher</Th>
                  <Th>Employee ID</Th>
                  <Th>Department</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {teachers.data.map((teacher) => (
                  <tr key={teacher.id}>
                    <Td>
                      <p className="font-medium text-ink">{teacher.full_name}</p>
                      <p className="text-[11px] text-muted">{teacher.email}</p>
                    </Td>
                    <Td className="font-mono text-xs">{teacher.teacher?.employee_id ?? "—"}</Td>
                    <Td className="text-xs text-muted">
                      {teacher.teacher?.department}
                      <span className="block">{teacher.teacher?.designation}</span>
                    </Td>
                    <Td>
                      <Badge tone={statusTone(teacher.status)}>{titleCase(teacher.status)}</Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Provision a teacher" description="The teacher can only create sessions for classes assigned to them." size="lg">
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" required>
            <Input value={form.full_name} onChange={(event) => set("full_name", event.target.value)} required />
          </Field>
          <Field label="Email" required>
            <Input type="email" value={form.email} onChange={(event) => set("email", event.target.value)} required />
          </Field>
          <Field label="Employee ID" required>
            <Input value={form.employee_id} onChange={(event) => set("employee_id", event.target.value)} required />
          </Field>
          <Field label="Department" required>
            <Input value={form.department} onChange={(event) => set("department", event.target.value)} required />
          </Field>
          <Field label="Designation">
            <Input value={form.designation} onChange={(event) => set("designation", event.target.value)} />
          </Field>
          <Field label="Password" hint="Leave blank to generate a temporary password.">
            <Input type="password" value={form.password} onChange={(event) => set("password", event.target.value)} />
          </Field>
          {error ? (
            <div className="sm:col-span-2">
              <Alert tone="danger">{error}</Alert>
            </div>
          ) : null}
          <div className="flex justify-end gap-2 sm:col-span-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              Create teacher
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
