"use client";

import { useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, PlayCircle, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState, type FormEvent } from "react";
import Link from "next/link";
import {
  Alert,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  PageHeader,
  Select,
  Switch,
} from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";
import { api, errorMessage } from "@/lib/api";
import type { ClassroomOut, GeofenceOut, Health, OpenSessionResponse, PolicyOut, SessionOut } from "@/lib/types";

interface TeacherAssignmentRow {
  assignment_id: string;
  class_id: string;
  class_name: string;
  class_code: string;
  subject_id: string | null;
  subject_name: string;
  subject_code: string | null;
  students: number;
}

interface TeacherClassRow {
  id: string;
  code: string;
  name: string;
  department: string;
  year: number;
  division: string;
  subjects: number;
  students: number;
}

function localInputValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export default function NewSessionPage() {
  const router = useRouter();
  const classes = useApiData<TeacherClassRow[]>("/teacher/classes");
  const assignments = useApiData<TeacherAssignmentRow[]>("/teacher/subjects");
  const classrooms = useApiData<ClassroomOut[]>("/classrooms");
  const policies = useApiData<PolicyOut[]>("/policies");
  const geofences = useApiData<GeofenceOut[]>("/geofences");
  const health = useApiData<Health>("/health/ready");

  const [classId, setClassId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [classroomId, setClassroomId] = useState("");
  const [startsAt, setStartsAt] = useState(() => localInputValue(new Date(Date.now() + 5 * 60 * 1000)));
  const [windowSeconds, setWindowSeconds] = useState("180");
  const [qrRefresh, setQrRefresh] = useState("30");
  const [policyId, setPolicyId] = useState("");
  const [geofenceId, setGeofenceId] = useState("");
  const [requirePin, setRequirePin] = useState(true);
  const [requireGeofence, setRequireGeofence] = useState(true);
  const [requireFace, setRequireFace] = useState(false);
  const [requireLiveness, setRequireLiveness] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const subjectsForClass = useMemo(
    () =>
      (assignments.data ?? []).filter(
        (assignment) => assignment.class_id === classId && assignment.subject_id,
      ),
    [assignments.data, classId],
  );

  useEffect(() => {
    if (classId && !subjectsForClass.some((item) => item.subject_id === subjectId)) {
      setSubjectId(subjectsForClass[0]?.subject_id ?? "");
    }
  }, [classId, subjectsForClass, subjectId]);

  useEffect(() => {
    if (!classroomId && classrooms.data?.length) {
      setClassroomId(classrooms.data[0].id);
    }
  }, [classrooms.data, classroomId]);

  useEffect(() => {
    if (!policyId && policies.data?.length) {
      const defaultPolicy = policies.data.find((policy) => policy.is_default) ?? policies.data[0];
      setPolicyId(defaultPolicy.id);
      setWindowSeconds(String(defaultPolicy.attendance_window_seconds));
      setQrRefresh(String(defaultPolicy.qr_refresh_seconds));
      setRequirePin(defaultPolicy.require_pin);
      setRequireGeofence(defaultPolicy.require_geofence);
      setRequireFace(defaultPolicy.require_face);
      setRequireLiveness(defaultPolicy.require_liveness);
    }
  }, [policies.data, policyId]);

  function applyPolicy(id: string) {
    setPolicyId(id);
    const policy = policies.data?.find((item) => item.id === id);
    if (!policy) return;
    setWindowSeconds(String(policy.attendance_window_seconds));
    setQrRefresh(String(policy.qr_refresh_seconds));
    setRequirePin(policy.require_pin);
    setRequireGeofence(policy.require_geofence);
    setRequireFace(policy.require_face);
    setRequireLiveness(policy.require_liveness);
    setGeofenceId("");
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!classId || !subjectId || !classroomId) {
      setError("Select an assigned class, a subject and a classroom.");
      return;
    }
    setSubmitting(true);
    try {
      const session = await api<SessionOut>("/teacher/sessions", {
        method: "POST",
        body: JSON.stringify({
          class_id: classId,
          subject_id: subjectId,
          classroom_id: classroomId,
          starts_at: new Date(startsAt).toISOString(),
          window_seconds: Number(windowSeconds),
          qr_refresh_seconds: Number(qrRefresh),
          policy_id: policyId || null,
          geofence_id: geofenceId || null,
          require_pin: requirePin,
          require_geofence: requireGeofence,
          require_face: requireFace,
          require_liveness: requireLiveness,
        }),
      });
      router.push(`/teacher/sessions/${session.id}`);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setSubmitting(false);
    }
  }

  const providersMissing =
    (requireFace && health.data?.face_provider === "none") ||
    (requireLiveness && health.data?.liveness_provider === "none");

  return (
    <div className="mx-auto max-w-4xl">
      <Link href="/teacher/sessions" className="mb-4 inline-flex items-center gap-1 text-xs font-medium text-muted hover:text-brand">
        <ArrowLeft size={14} /> Back to sessions
      </Link>
      <PageHeader
        eyebrow="Start attendance"
        title="Configure a verified attendance session"
        description="Only classes and subjects assigned to you can be selected. The backend re-validates the assignment before creating the session."
      />

      {error ? (
        <div className="mb-4">
          <Alert tone="danger" title="Session could not be created">
            {error}
          </Alert>
        </div>
      ) : null}

      <form onSubmit={onSubmit} className="grid gap-5 lg:grid-cols-[1.25fr_1fr]">
        <Card>
          <CardHeader title="Session details" description="Class, subject, room and timing." />
          <div className="space-y-4 p-5">
            <Field label="Class" required>
              <Select
                value={classId}
                onChange={(event) => setClassId(event.target.value)}
                required
                data-testid="class-select"
              >
                <option value="">Select an assigned class</option>
                {(classes.data ?? []).map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name} ({item.code}) · {item.students} students
                  </option>
                ))}
              </Select>
              {classes.data?.length === 0 ? (
                <p className="mt-1 text-xs text-danger">
                  No classes are assigned to you yet. Ask an administrator to create a teaching
                  assignment.
                </p>
              ) : null}
            </Field>

            <Field label="Subject" required>
              <Select
                value={subjectId}
                onChange={(event) => setSubjectId(event.target.value)}
                disabled={!classId}
                required
                data-testid="subject-select"
              >
                <option value="">Select a subject</option>
                {subjectsForClass.map((item) => (
                  <option key={item.assignment_id} value={item.subject_id ?? ""}>
                    {item.subject_name} {item.subject_code ? `(${item.subject_code})` : ""}
                  </option>
                ))}
              </Select>
            </Field>

            <Field label="Classroom" required>
              <Select
                value={classroomId}
                onChange={(event) => setClassroomId(event.target.value)}
                required
                data-testid="classroom-select"
              >
                <option value="">Select a classroom</option>
                {(classrooms.data ?? []).map((room) => (
                  <option key={room.id} value={room.id}>
                    {room.name} · {room.building ?? "Campus"} · radius {room.default_radius_m} m
                  </option>
                ))}
              </Select>
            </Field>

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Start time" hint="Local time. The window starts when you open the session." required>
                <Input
                  type="datetime-local"
                  value={startsAt}
                  onChange={(event) => setStartsAt(event.target.value)}
                  required
                />
              </Field>
              <Field label="Attendance window">
                <Select value={windowSeconds} onChange={(event) => setWindowSeconds(event.target.value)}>
                  <option value="120">2 minutes</option>
                  <option value="180">3 minutes (default)</option>
                  <option value="300">5 minutes</option>
                  <option value="600">10 minutes</option>
                </Select>
              </Field>
            </div>

            <Field label="QR refresh interval" hint="Independent of the attendance window.">
              <Select value={qrRefresh} onChange={(event) => setQrRefresh(event.target.value)}>
                <option value="15">15 seconds</option>
                <option value="30">30 seconds (default)</option>
                <option value="60">60 seconds</option>
              </Select>
            </Field>
          </div>
        </Card>

        <div className="space-y-5">
          <Card>
            <CardHeader title="Verification requirements" description="Policy defaults are copied into this session." />
            <div className="divide-y divide-line px-5 py-2">
              <Switch
                checked={requirePin}
                onChange={setRequirePin}
                label="Temporary PIN"
                hint="Recommended. Attempt-limited and invalidated on close."
              />
              <Switch
                checked={requireGeofence}
                onChange={setRequireGeofence}
                label="Location evidence"
                hint="Evaluated server-side against the classroom geofence."
              />
              <Switch
                checked={requireFace}
                onChange={setRequireFace}
                label="Face verification"
                hint="Requires a configured provider and student consent/enrolment."
              />
              <Switch
                checked={requireLiveness}
                onChange={setRequireLiveness}
                label="Liveness detection"
                hint="Separate provider contract; unavailable is reported honestly."
              />
            </div>
            {providersMissing ? (
              <div className="border-t border-line p-4">
                <Alert tone="warning" title="Provider not configured">
                  This deployment does not have the selected face/liveness provider configured.
                  Students will receive an honest UNAVAILABLE state, and affected attempts will be
                  routed to teacher review rather than fabricated as passed.
                </Alert>
              </div>
            ) : null}
          </Card>

          <Card>
            <CardHeader title="Policy and geofence" description="Optional overrides for this session." />
            <div className="space-y-4 p-5">
              <Field label="Attendance policy">
                <Select value={policyId} onChange={(event) => applyPolicy(event.target.value)}>
                  <option value="">Use built-in defaults</option>
                  {(policies.data ?? []).map((policy) => (
                    <option key={policy.id} value={policy.id}>
                      {policy.name} {policy.is_default ? "(default)" : ""}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field
                label="Geofence override"
                hint="Leave empty to use the classroom's configured centre and radius."
              >
                <Select value={geofenceId} onChange={(event) => setGeofenceId(event.target.value)}>
                  <option value="">Use classroom geofence</option>
                  {(geofences.data ?? []).map((fence) => (
                    <option key={fence.id} value={fence.id}>
                      {fence.name} · {fence.radius_m} m
                    </option>
                  ))}
                </Select>
              </Field>
            </div>
          </Card>

          <div className="rounded-xl border border-[#D4E3FF] bg-[#F5F9FF] p-4 text-xs leading-relaxed text-[#1F3D7A]">
            <ShieldCheck size={16} className="mb-2 text-brand" />
            The session is created in a <strong>scheduled</strong> state. Opening it generates the
            first signed QR token and the temporary PIN. QR rotation never invalidates another
            student&apos;s already-started attempt.
          </div>

          <Button type="submit" size="lg" loading={submitting} className="w-full" data-testid="create-session">
            <PlayCircle size={17} /> Create session
          </Button>
          <p className="text-center text-[11px] text-muted">
            You will be taken to the live session screen, where you can open the attendance window.
          </p>
        </div>
      </form>
    </div>
  );
}
