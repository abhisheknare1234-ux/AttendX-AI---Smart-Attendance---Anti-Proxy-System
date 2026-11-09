"use client";

import { Plus, SlidersHorizontal } from "lucide-react";
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
  Switch,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage } from "@/lib/api";
import type { PolicyOut } from "@/lib/types";

const emptyForm = {
  name: "",
  is_default: false,
  attendance_window_seconds: "180",
  qr_refresh_seconds: "30",
  qr_grace_seconds: "15",
  require_pin: true,
  require_geofence: true,
  require_face: false,
  require_liveness: false,
  allow_review_outside_geofence: true,
  presence_monitoring_enabled: false,
};

export default function AdminPoliciesPage() {
  const policies = useApiData<PolicyOut[]>("/admin/policies");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<string | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setError(null);
    setOpen(true);
  }

  function openEdit(policy: PolicyOut) {
    setEditing(policy.id);
    setForm({
      name: policy.name,
      is_default: policy.is_default,
      attendance_window_seconds: String(policy.attendance_window_seconds),
      qr_refresh_seconds: String(policy.qr_refresh_seconds),
      qr_grace_seconds: String(policy.qr_grace_seconds),
      require_pin: policy.require_pin,
      require_geofence: policy.require_geofence,
      require_face: policy.require_face,
      require_liveness: policy.require_liveness,
      allow_review_outside_geofence: policy.allow_review_outside_geofence,
      presence_monitoring_enabled: policy.presence_monitoring_enabled,
    });
    setError(null);
    setOpen(true);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const payload = {
      ...form,
      attendance_window_seconds: Number(form.attendance_window_seconds),
      qr_refresh_seconds: Number(form.qr_refresh_seconds),
      qr_grace_seconds: Number(form.qr_grace_seconds),
    };
    try {
      if (editing) {
        await api(`/admin/policies/${editing}`, {
          method: "PATCH",
          body: JSON.stringify(payload),
        });
      } else {
        await api("/admin/policies", { method: "POST", body: JSON.stringify(payload) });
      }
      setOpen(false);
      await policies.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  async function makeDefault(policy: PolicyOut) {
    try {
      await api(`/admin/policies/${policy.id}`, {
        method: "PATCH",
        body: JSON.stringify({ is_default: true }),
      });
      await policies.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Attendance policy"
        title="Institutional attendance policies"
        description="Sessions snapshot these settings when created. The attendance window and QR refresh interval are independent."
        actions={
          <Button onClick={openCreate}>
            <Plus size={15} /> Create policy
          </Button>
        }
      />
      {error ? (
        <div className="mb-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}
      <Card>
        <CardHeader title={`${policies.data?.length ?? 0} policies`} action={<SlidersHorizontal size={16} className="text-muted" />} />
        {policies.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : !policies.data?.length ? (
          <p className="p-5 text-sm text-muted">No policies configured. Built-in defaults apply to sessions.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Policy</Th>
                  <Th>Window / refresh</Th>
                  <Th>Required factors</Th>
                  <Th>Default</Th>
                  <Th />
                </tr>
              </thead>
              <tbody>
                {policies.data.map((policy) => (
                  <tr key={policy.id}>
                    <Td className="font-medium text-ink">{policy.name}</Td>
                    <Td className="text-xs text-muted">
                      {policy.attendance_window_seconds}s window
                      <span className="block">{policy.qr_refresh_seconds}s QR refresh</span>
                    </Td>
                    <Td>
                      <div className="flex flex-wrap gap-1">
                        {policy.require_pin ? <Badge tone="blue">PIN</Badge> : null}
                        {policy.require_geofence ? <Badge tone="blue">Location</Badge> : null}
                        {policy.require_face ? <Badge tone="blue">Face</Badge> : null}
                        {policy.require_liveness ? <Badge tone="blue">Liveness</Badge> : null}
                      </div>
                    </Td>
                    <Td>
                      {policy.is_default ? (
                        <Badge tone="green">Default</Badge>
                      ) : (
                        <Button size="sm" variant="ghost" onClick={() => void makeDefault(policy)}>
                          Make default
                        </Button>
                      )}
                    </Td>
                    <Td className="text-right">
                      <Button size="sm" variant="secondary" onClick={() => openEdit(policy)}>
                        Edit
                      </Button>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title={editing ? "Edit attendance policy" : "Create attendance policy"} description="These constraints are copied into each new session." size="lg">
        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Policy name" required>
              <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
            </Field>
            <Field label="Window (seconds)" hint="How long check-in remains open after the teacher opens the session.">
              <Input
                type="number"
                value={form.attendance_window_seconds}
                onChange={(event) => setForm({ ...form, attendance_window_seconds: event.target.value })}
                min={30}
              />
            </Field>
            <Field label="QR refresh (seconds)">
              <Input
                type="number"
                value={form.qr_refresh_seconds}
                onChange={(event) => setForm({ ...form, qr_refresh_seconds: event.target.value })}
                min={5}
              />
            </Field>
            <Field label="QR grace (seconds)" hint="Old rotated tokens stay valid for this short processing window.">
              <Input
                type="number"
                value={form.qr_grace_seconds}
                onChange={(event) => setForm({ ...form, qr_grace_seconds: event.target.value })}
                min={0}
              />
            </Field>
          </div>
          <div className="grid gap-2 rounded-lg border border-line p-4 sm:grid-cols-2">
            <Switch checked={form.require_pin} onChange={(value) => setForm({ ...form, require_pin: value })} label="Require PIN" />
            <Switch checked={form.require_geofence} onChange={(value) => setForm({ ...form, require_geofence: value })} label="Require location" />
            <Switch checked={form.require_face} onChange={(value) => setForm({ ...form, require_face: value })} label="Require face" />
            <Switch checked={form.require_liveness} onChange={(value) => setForm({ ...form, require_liveness: value })} label="Require liveness" />
            <Switch
              checked={form.allow_review_outside_geofence}
              onChange={(value) => setForm({ ...form, allow_review_outside_geofence: value })}
              label="Review outside geofence"
              hint="Otherwise an outside fix is rejected."
            />
            <Switch
              checked={form.is_default}
              onChange={(value) => setForm({ ...form, is_default: value })}
              label="Use as institution default"
            />
          </div>
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              {editing ? "Save policy" : "Create policy"}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
