"use client";

import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import {
  Alert,
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
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage } from "@/lib/api";
import type { ClassOut, SubjectOut } from "@/lib/types";

export default function AdminSubjectsPage() {
  const subjects = useApiData<SubjectOut[]>("/admin/subjects");
  const classes = useApiData<ClassOut[]>("/admin/classes");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ code: "", name: "", class_id: "", credits: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/admin/subjects", {
        method: "POST",
        body: JSON.stringify({
          code: form.code,
          name: form.name,
          class_id: form.class_id,
          credits: form.credits ? Number(form.credits) : null,
        }),
      });
      setOpen(false);
      setForm({ code: "", name: "", class_id: "", credits: "" });
      await subjects.reload();
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
        title="Subjects"
        description="Each subject belongs to exactly one class. Sessions bind a subject to its class and classroom."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Add subject
          </Button>
        }
      />
      <Card>
        <CardHeader title={`${subjects.data?.length ?? 0} subjects`} />
        {subjects.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : !subjects.data?.length ? (
          <p className="p-5 text-sm text-muted">No subjects configured.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Subject</Th>
                  <Th>Class</Th>
                  <Th>Credits</Th>
                  <Th>Status</Th>
                </tr>
              </thead>
              <tbody>
                {subjects.data.map((item) => (
                  <tr key={item.id}>
                    <Td>
                      <p className="font-medium text-ink">{item.name}</p>
                      <p className="font-mono text-[11px] text-muted">{item.code}</p>
                    </Td>
                    <Td className="text-xs text-muted">
                      {item.class_name ?? "—"}
                      <span className="block">{item.class_code}</span>
                    </Td>
                    <Td className="text-xs text-muted">{item.credits ?? "—"}</Td>
                    <Td className="text-xs text-muted">{item.is_active ? "Active" : "Inactive"}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Create a subject" description="Subject codes are unique.">
        <form onSubmit={submit} className="space-y-4">
          <Field label="Class" required>
            <Select value={form.class_id} onChange={(event) => setForm({ ...form, class_id: event.target.value })} required>
              <option value="">Select a class</option>
              {(classes.data ?? []).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} ({item.code})
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Subject code" required>
            <Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} placeholder="CS301" required />
          </Field>
          <Field label="Subject name" required>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Database Management Systems" required />
          </Field>
          <Field label="Credits">
            <Input type="number" value={form.credits} onChange={(event) => setForm({ ...form, credits: event.target.value })} />
          </Field>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              Create subject
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
