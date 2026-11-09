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
  Switch,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage } from "@/lib/api";
import type { ClassroomOut, GeofenceOut } from "@/lib/types";

export default function AdminGeofencesPage() {
  const geofences = useApiData<GeofenceOut[]>("/admin/geofences");
  const classrooms = useApiData<ClassroomOut[]>("/admin/classrooms");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    name: "",
    classroom_id: "",
    radius_m: "60",
    max_accuracy_m: "100",
    allow_review_outside: true,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function selectedClassroom(): ClassroomOut | undefined {
    return (classrooms.data ?? []).find((room) => room.id === form.classroom_id);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const room = selectedClassroom();
    if (!room) {
      setError("Select a classroom to anchor the geofence.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api("/admin/geofences", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          classroom_id: form.classroom_id,
          center_latitude: room.latitude,
          center_longitude: room.longitude,
          radius_m: Number(form.radius_m),
          max_accuracy_m: Number(form.max_accuracy_m),
          allow_review_outside: form.allow_review_outside,
        }),
      });
      setOpen(false);
      setForm({ name: "", classroom_id: "", radius_m: "60", max_accuracy_m: "100", allow_review_outside: true });
      await geofences.reload();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Location configuration"
        title="Geofence policies"
        description="Geofences define the classroom centre, radius and accuracy tolerance used for server-side location evidence."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Add geofence
          </Button>
        }
      />
      <Card>
        <CardHeader title={`${geofences.data?.length ?? 0} geofences`} />
        {geofences.loading ? (
          <div className="p-4">
            <Skeleton className="h-48" />
          </div>
        ) : !geofences.data?.length ? (
          <p className="p-5 text-sm text-muted">
            No geofences configured. Sessions fall back to the classroom geofence.
          </p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Geofence</Th>
                  <Th>Centre</Th>
                  <Th>Radius</Th>
                  <Th>Accuracy limit</Th>
                  <Th>Outside fix</Th>
                </tr>
              </thead>
              <tbody>
                {geofences.data.map((fence) => (
                  <tr key={fence.id}>
                    <Td className="font-medium text-ink">{fence.name}</Td>
                    <Td className="font-mono text-[11px] text-muted">
                      {fence.center_latitude.toFixed(5)}, {fence.center_longitude.toFixed(5)}
                    </Td>
                    <Td className="text-xs text-muted">{fence.radius_m} m</Td>
                    <Td className="text-xs text-muted">{fence.max_accuracy_m} m</Td>
                    <Td>
                      <Badge tone={fence.allow_review_outside ? "amber" : "red"}>
                        {fence.allow_review_outside ? "Review" : "Reject"}
                      </Badge>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Create a geofence" description="Coordinates are taken from the selected classroom.">
        <form onSubmit={submit} className="space-y-4">
          <Field label="Name" required>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Block A — Lab 101 strict" required />
          </Field>
          <Field label="Classroom" required>
            <Select value={form.classroom_id} onChange={(event) => setForm({ ...form, classroom_id: event.target.value })} required>
              <option value="">Select a classroom</option>
              {(classrooms.data ?? []).map((room) => (
                <option key={room.id} value={room.id}>
                  {room.name} · {room.code}
                </option>
              ))}
            </Select>
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Radius (m)">
              <Input type="number" value={form.radius_m} onChange={(event) => setForm({ ...form, radius_m: event.target.value })} />
            </Field>
            <Field label="Max accuracy (m)">
              <Input
                type="number"
                value={form.max_accuracy_m}
                onChange={(event) => setForm({ ...form, max_accuracy_m: event.target.value })}
              />
            </Field>
          </div>
          <Switch
            checked={form.allow_review_outside}
            onChange={(value) => setForm({ ...form, allow_review_outside: value })}
            label="Allow teacher review outside the radius"
            hint="When disabled, an outside fix is rejected by policy."
          />
          {error ? <Alert tone="danger">{error}</Alert> : null}
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={busy}>
              Create geofence
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
