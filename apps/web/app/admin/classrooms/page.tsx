"use client";

import { MapPin, Plus } from "lucide-react";
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
  Skeleton,
  Table,
  TableWrap,
  Td,
  Th,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage } from "@/lib/api";
import type { ClassroomOut } from "@/lib/types";

export default function AdminClassroomsPage() {
  const rooms = useApiData<ClassroomOut[]>("/admin/classrooms");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({
    code: "",
    name: "",
    building: "",
    floor: "",
    latitude: "18.5204",
    longitude: "73.8567",
    default_radius_m: "60",
    max_accuracy_m: "100",
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/admin/classrooms", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          building: form.building || null,
          floor: form.floor || null,
          latitude: Number(form.latitude),
          longitude: Number(form.longitude),
          default_radius_m: Number(form.default_radius_m),
          max_accuracy_m: Number(form.max_accuracy_m),
        }),
      });
      setOpen(false);
      await rooms.reload();
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
        title="Classrooms"
        description="Classroom coordinates anchor the default geofence. GPS is treated as evidence, not proof of exact presence."
        actions={
          <Button onClick={() => setOpen(true)}>
            <Plus size={15} /> Add classroom
          </Button>
        }
      />
      <Card>
        <CardHeader title={`${rooms.data?.length ?? 0} classrooms`} />
        {rooms.loading ? (
          <div className="p-4">
            <Skeleton className="h-52" />
          </div>
        ) : !rooms.data?.length ? (
          <p className="p-5 text-sm text-muted">No classrooms configured.</p>
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Classroom</Th>
                  <Th>Building / floor</Th>
                  <Th>Coordinates</Th>
                  <Th>Radius</Th>
                  <Th>Max accuracy</Th>
                </tr>
              </thead>
              <tbody>
                {rooms.data.map((room) => (
                  <tr key={room.id}>
                    <Td>
                      <p className="font-medium text-ink">{room.name}</p>
                      <p className="font-mono text-[11px] text-muted">{room.code}</p>
                    </Td>
                    <Td className="text-xs text-muted">
                      {room.building ?? "—"}
                      <span className="block">{room.floor ?? ""}</span>
                    </Td>
                    <Td className="font-mono text-[11px] text-muted">
                      {room.latitude.toFixed(5)}, {room.longitude.toFixed(5)}
                    </Td>
                    <Td className="text-xs text-muted">{room.default_radius_m} m</Td>
                    <Td className="text-xs text-muted">{room.max_accuracy_m} m</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>

      <Modal open={open} onClose={() => setOpen(false)} title="Add a classroom" description="Coordinates should come from an authoritative campus survey." size="lg">
        <form onSubmit={submit} className="grid gap-4 sm:grid-cols-2">
          <Field label="Code" required>
            <Input value={form.code} onChange={(event) => setForm({ ...form, code: event.target.value })} placeholder="R-101" required />
          </Field>
          <Field label="Name" required>
            <Input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Computer Lab 101" required />
          </Field>
          <Field label="Building">
            <Input value={form.building} onChange={(event) => setForm({ ...form, building: event.target.value })} />
          </Field>
          <Field label="Floor">
            <Input value={form.floor} onChange={(event) => setForm({ ...form, floor: event.target.value })} />
          </Field>
          <Field label="Latitude" required>
            <Input type="number" step="0.000001" value={form.latitude} onChange={(event) => setForm({ ...form, latitude: event.target.value })} required />
          </Field>
          <Field label="Longitude" required>
            <Input type="number" step="0.000001" value={form.longitude} onChange={(event) => setForm({ ...form, longitude: event.target.value })} required />
          </Field>
          <Field label="Default radius (m)">
            <Input type="number" value={form.default_radius_m} onChange={(event) => setForm({ ...form, default_radius_m: event.target.value })} />
          </Field>
          <Field label="Maximum GPS accuracy (m)" hint="Fixes worse than this are recorded as low accuracy.">
            <Input type="number" value={form.max_accuracy_m} onChange={(event) => setForm({ ...form, max_accuracy_m: event.target.value })} />
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
              <MapPin size={15} /> Create classroom
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
