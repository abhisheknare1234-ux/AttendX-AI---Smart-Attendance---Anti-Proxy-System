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
  Select,
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

export default function AdminStudentsPage() {
  const students = useApiData<User[]>("/admin/students?limit=300");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    email: "",
    full_name: "",
    password: "",
    roll_number: "",
    department: "Computer Engineering",
    programme: "B.E.",
    year: "1",
    division: "A",
    batch: "",
    admission_year: "",
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
      const result = await api<{ user: User; temporary_password: string | null }>("/admin/students", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          year: Number(form.year),
          admission_year: form.admission_year ? Number(form.admission_year) : null,
          password: form.password || null,
          batch: form.batch || null,
        }),
      });
      if (result.temporary_password) setTemp({ email: result.user.email, password: result.temporary_password });
      setOpen(false);
      setForm((current) => ({ ...current, email: "", full_name: "", password: "", roll_number: "" }));
      await students.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Students"
        title="Student accounts"
        description="Provisioned accounts with roll numbers and academic details. Use CSV import on the Users page for bulk onboarding."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Add student
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
        <CardHeader title={`${students.data?.length ?? 0} student account(s)`} />
        {students.loading ? (
          <div className="p-4">
            <Skeleton className="h-56" />
          </div>
        ) : !students.data?.length ? (
          <p className="p-5 text-sm text-muted">No students provisioned yet.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Student</Th>
                  <Th>Roll number</Th>
                  <Th>Programme</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {students.data.map((student) => (
                  <tr key={student.id}>
                    <Td>
                      <p className="font-medium text-ink">{student.full_name}</p>
                      <p className="text-[11px] text-muted">{student.email}</p>
                    </Td>
                    <Td className="font-mono text-xs text-ink">{student.student?.roll_number ?? "—"}</Td>
                    <Td className="text-xs text-muted">
                      {student.student
                        ? `${student.student.programme} · Year ${student.student.year} · Div ${student.student.division}`
                        : "—"}
                      <span className="block">{student.student?.department}</span>
                    </Td>
                    <Td>
                      <Badge tone={statusTone(student.status)}>{titleCase(student.status)}</Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Provision a student" description="A temporary password is generated unless you set one." size="lg">
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Field label="Full name" required>
            <Input value={form.full_name} onChange={(event) => set("full_name", event.target.value)} required />
          </Field>
          <Field label="Email" required>
            <Input type="email" value={form.email} onChange={(event) => set("email", event.target.value)} required />
          </Field>
          <Field label="Roll number" required>
            <Input value={form.roll_number} onChange={(event) => set("roll_number", event.target.value)} required />
          </Field>
          <Field label="Department" required>
            <Input value={form.department} onChange={(event) => set("department", event.target.value)} required />
          </Field>
          <Field label="Programme">
            <Input value={form.programme} onChange={(event) => set("programme", event.target.value)} />
          </Field>
          <Field label="Year">
            <Select value={form.year} onChange={(event) => set("year", event.target.value)}>
              {[1, 2, 3, 4].map((year) => (
                <option key={year} value={year}>
                  Year {year}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Division">
            <Input value={form.division} onChange={(event) => set("division", event.target.value)} />
          </Field>
          <Field label="Admission year">
            <Input type="number" value={form.admission_year} onChange={(event) => set("admission_year", event.target.value)} />
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
              Create student
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
