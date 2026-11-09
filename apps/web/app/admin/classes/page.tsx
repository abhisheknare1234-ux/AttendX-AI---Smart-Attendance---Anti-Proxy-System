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
import { api, errorMessage } from "@/lib/api";
import type { ClassOut } from "@/lib/types";

export default function AdminClassesPage() {
  const classes = useApiData<ClassOut[]>("/admin/classes");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", department: "Computer Engineering", year: "1", division: "A" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/admin/classes", {
        method: "POST",
        body: JSON.stringify({ ...form, year: Number(form.year) }),
      });
      setOpen(false);
      setForm({ code: "", name: "", department: "Computer Engineering", year: "1", division: "A" });
      await classes.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Academic configuration"
        title="Classes"
        description="A class groups students for enrolment. Subjects belong to a class; teachers are assigned to class/subject pairs."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Add class
          </Button>
        }
      />
      <Card>
        <CardHeader title={`${classes.data?.length ?? 0} classes`} />
        {classes.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : !classes.data?.length ? (
          <p className="p-5 text-sm text-muted">No classes configured.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Class</Th>
                  <Th>Department</Th>
                  <Th>Year / division</Th>
                  <Th>Enrolled</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {classes.data.map((item) => (
                  <tr key={item.id}>
                    <Td>
                      <p className="font-medium text-ink">{item.name}</p>
                      <p className="font-mono text-[11px] text-muted">{item.code}</p>
                    </Td>
                    <Td className="text-xs text-muted">{item.department}</Td>
                    <Td className="text-xs text-muted">
                      {item.year} / {item.division}
                    </Td>
                    <Td className="text-sm font-medium text-ink">{item.enrolled_count}</Td>
                    <Td>
                      <Badge tone={statusTone(item.is_active ? "active" : "disabled")}>
                        {item.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Create a class" description="Class codes are unique across the institution.">
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Field label="Class code" required>
            <Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} placeholder="CE-2024-A" required />
          </Field>
          <Field label="Display name" required>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="TE Computer A" required />
          </Field>
          <Field label="Department" required>
            <Input value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value })} required />
          </Field>
          <Field label="Year">
            <Select value={form.year} onChange={(event) => setForm({ ...form, year: event.target.value })}>
              {[1, 2, 3, 4].map((year) => (
                <option key={year} value={year}>
                  Year {year}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Division">
            <Input value={form.division} onChange={(event) => setForm({ ...form, division: event.target.value })} />
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
              Create class
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
