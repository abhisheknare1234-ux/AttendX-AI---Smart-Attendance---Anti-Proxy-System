export type Role = "admin" | "teacher" | "student";

export interface StudentSummary {
  id: string;
  roll_number: string;
  department: string;
  programme: string;
  year: number;
  division: string;
  batch: string | null;
}

export interface TeacherSummary {
  id: string;
  employee_id: string;
  department: string;
  designation: string | null;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  status: "active" | "disabled" | "locked";
  must_change_password: boolean;
  last_login_at: string | null;
  created_at: string;
  student: StudentSummary | null;
  teacher: TeacherSummary | null;
}

export interface MeResponse {
  user: User;
  csrf_token: string;
}

export interface ClassOut {
  id: string;
  code: string;
  name: string;
  department: string;
  year: number;
  division: string;
  is_active: boolean;
  created_at: string;
  enrolled_count: number;
}

export interface SubjectOut {
  id: string;
  code: string;
  name: string;
  class_id: string;
  class_code: string | null;
  class_name: string | null;
  credits: number | null;
  is_active: boolean;
}

export interface ClassroomOut {
  id: string;
  code: string;
  name: string;
  building: string | null;
  floor: string | null;
  latitude: number;
  longitude: number;
  default_radius_m: number;
  max_accuracy_m: number;
  is_active: boolean;
}

export interface PolicyOut {
  id: string;
  name: string;
  is_default: boolean;
  attendance_window_seconds: number;
  qr_refresh_seconds: number;
  qr_grace_seconds: number;
  require_pin: boolean;
  require_geofence: boolean;
  require_face: boolean;
  require_liveness: boolean;
  allow_review_outside_geofence: boolean;
  presence_monitoring_enabled: boolean;
  full_presence_ratio: number;
  partial_presence_ratio: number;
}

export interface GeofenceOut {
  id: string;
  name: string;
  classroom_id: string | null;
  center_latitude: number;
  center_longitude: number;
  radius_m: number;
  max_accuracy_m: number;
  allow_review_outside: boolean;
  is_active: boolean;
}

export interface EnrollmentOut {
  id: string;
  class_id: string;
  class_name: string;
  student_id: string;
  student_name: string;
  roll_number: string;
  status: "active" | "dropped";
  enrolled_at: string;
}

export interface AssignmentOut {
  id: string;
  teacher_id: string;
  teacher_name: string;
  class_id: string;
  class_name: string;
  subject_id: string | null;
  subject_name: string | null;
  is_active: boolean;
  assigned_at: string;
}

export type SessionStatus = "scheduled" | "open" | "closed" | "cancelled" | "expired";

export interface SessionOut {
  id: string;
  class_id: string;
  class_code: string;
  class_name: string;
  subject_id: string;
  subject_code: string;
  subject_name: string;
  classroom_id: string;
  classroom_name: string;
  teacher_id: string;
  teacher_name: string;
  status: SessionStatus;
  starts_at: string;
  ends_at: string;
  window_seconds: number;
  qr_refresh_seconds: number;
  qr_grace_seconds: number;
  require_pin: boolean;
  require_geofence: boolean;
  require_face: boolean;
  require_liveness: boolean;
  allow_review_outside_geofence: boolean;
  pin_available: boolean;
  opened_at: string | null;
  closed_at: string | null;
  created_at: string;
  eligible_students: number;
  accepted: number;
  pending: number;
  rejected: number;
  review_required: number;
}

export interface QrOut {
  token: string;
  url: string;
  issued_at: string;
  expires_at: string;
  refresh_seconds: number;
  session_id: string;
}

export interface OpenSessionResponse {
  session: SessionOut;
  pin: string | null;
  pin_expires_at: string | null;
  qr: QrOut;
}

export interface LiveAttempt {
  attempt_id: string;
  reference: string;
  student_name: string;
  roll_number: string;
  status: string;
  current_step: string;
  gps_status: string;
  face_status: string;
  liveness_status: string;
  risk_decision: string | null;
  created_at: string;
}

export interface LiveSessionResponse {
  session: SessionOut;
  qr: QrOut | null;
  seconds_remaining: number;
  recent_attempts: LiveAttempt[];
}

export interface Requirements {
  pin: boolean;
  geofence: boolean;
  face: boolean;
  liveness: boolean;
}

export interface QrValidateResponse {
  session_id: string;
  class_name: string;
  subject_name: string;
  classroom_name: string;
  teacher_name: string;
  status: SessionStatus;
  starts_at: string;
  ends_at: string;
  seconds_remaining: number;
  requirements: Requirements;
  already_recorded: boolean;
  existing_status: string | null;
  can_check_in: boolean;
  message: string;
}

export type AttemptStatus =
  | "in_progress"
  | "accepted"
  | "rejected"
  | "review_required"
  | "expired"
  | "abandoned";

export interface Attempt {
  id: string;
  reference: string;
  session_id: string;
  status: AttemptStatus;
  current_step: string;
  qr_status: string;
  pin_status: string;
  gps_status: string;
  face_status: string;
  liveness_status: string;
  pin_attempts: number;
  gps_distance_m: number | null;
  gps_accuracy_m: number | null;
  risk_score: number;
  risk_decision: string | null;
  risk_reasons: Array<{ code: string; factor: string; severity: string; message: string }> | null;
  created_at: string;
  completed_at: string | null;
}

export interface CheckInResponse {
  attempt: Attempt;
  session: QrValidateResponse;
  required_steps: Array<"pin" | "gps" | "face" | "liveness">;
  next_step: string | null;
}

export interface StepResponse {
  attempt: Attempt;
  next_step: string | null;
  message: string;
}

export interface FactorStepResponse extends StepResponse {
  factor: string;
  status: string;
  reason_code: string | null;
  provider: string | null;
  score: number | null;
}

export interface LocationStepResponse extends StepResponse {
  gps_status: string;
  distance_m: number | null;
  accuracy_m: number | null;
  reason_code: string | null;
}

export interface FinalizeResponse {
  record_id: string;
  reference: string;
  session_id: string;
  status: "present" | "absent" | "review_required" | "rejected";
  classification: string;
  decision_source: string;
  decision: "ACCEPTED" | "REJECTED" | "REVIEW_REQUIRED";
  risk_score: number;
  reasons: Array<{ code: string; factor: string; severity: string; message: string }>;
  check_in_at: string | null;
}

export interface HistoryItem {
  record_id: string;
  reference: string;
  session_id: string;
  subject_name: string;
  subject_code: string;
  class_name: string;
  status: string;
  classification: string;
  decision_source: string;
  check_in_at: string | null;
  session_starts_at: string;
  session_ends_at: string;
}

export interface SubjectSummary {
  subject_id: string;
  subject_name: string;
  subject_code: string;
  class_name: string;
  sessions: number;
  present: number;
  percentage: number | null;
}

export interface ActiveSessionSummary {
  session_id: string;
  subject_name: string;
  class_name: string;
  status: SessionStatus;
  ends_at: string;
  seconds_remaining: number;
}

export interface StudentDashboard {
  student_name: string;
  roll_number: string;
  total_sessions: number;
  attended_sessions: number;
  attendance_percentage: number | null;
  pending_reviews: number;
  active_sessions: ActiveSessionSummary[];
  upcoming_sessions: ActiveSessionSummary[];
  subjects: SubjectSummary[];
  recent_records: HistoryItem[];
}

export interface Review {
  id: string;
  session_id: string;
  subject_name: string;
  class_name: string;
  student_id: string;
  student_name: string;
  roll_number: string;
  reason: string;
  status: "open" | "approved" | "rejected" | "withdrawn";
  attempt_reference: string | null;
  record_reference: string | null;
  risk_decision: string | null;
  risk_score: number | null;
  risk_reasons: Array<{ code: string; factor: string; severity: string; message: string }> | null;
  session_starts_at: string;
  created_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
}

export interface TeacherDashboard {
  teacher_name: string;
  classes_count: number;
  subjects_count: number;
  students_count: number;
  active_sessions: number;
  today_sessions: number;
  present_today: number;
  review_pending: number;
  failed_attempts_today: number;
  recent_sessions: SessionOut[];
  review_queue: Review[];
}

export interface ReportRow {
  student_id: string;
  student_name: string;
  roll_number: string;
  class_name: string;
  subject_name: string;
  sessions_held: number;
  sessions_present: number;
  attendance_percentage: number | null;
}

export interface ReportResponse {
  generated_at: string;
  filters: Record<string, string | null>;
  totals: {
    students?: number;
    sessions?: number;
    present?: number;
    average_percentage?: number | null;
  };
  rows: ReportRow[];
}

export interface AuditEvent {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface SecurityEvent {
  id: string;
  event_type: string;
  severity: string;
  user_id: string | null;
  session_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface Health {
  status: string;
  database: string;
  face_provider: string;
  liveness_provider: string;
  environment: string;
  version: string;
}

export interface FaceEnrollment {
  status: "not_enrolled" | "pending" | "active" | "deleted";
  provider: string;
  model_name: string | null;
  model_version: string | null;
  consent_version: string | null;
  consented_at: string | null;
  deleted_at: string | null;
  dimension: number | null;
  local_face_available: boolean;
  liveness_provider: string;
}

export interface ImportPreview {
  kind: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  rows: Array<{
    row_number: number;
    ok: boolean;
    errors: string[];
    data: Record<string, string>;
  }>;
}

export interface ImportCommit {
  job_id: string;
  status: string;
  total_rows: number;
  success_rows: number;
  error_rows: number;
  errors: Array<Record<string, unknown>>;
  created_users: Array<{
    id: string;
    email: string;
    full_name: string;
    role: string;
    temporary_password: string | null;
  }>;
}
