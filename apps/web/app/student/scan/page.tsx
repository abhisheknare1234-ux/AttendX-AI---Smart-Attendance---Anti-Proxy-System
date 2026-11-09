"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, KeyRound, QrCode, ShieldCheck, Smartphone } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Alert, Button, Card, CardHeader, Field, Input, PageHeader } from "@/components/ui";
import { QrScanner } from "@/components/scanner";

function extractToken(raw: string): string | null {
  const value = raw.trim();
  if (!value) return null;
  try {
    const url = new URL(value);
    const match = url.pathname.match(/\/attend\/([^/]+)$/);
    if (match) return decodeURIComponent(match[1]);
    return null;
  } catch {
    if (value.startsWith("v1.")) return value;
    return null;
  }
}

export default function StudentScanPage() {
  const router = useRouter();
  const [manual, setManual] = useState("");
  const [error, setError] = useState<string | null>(null);

  function go(raw: string) {
    const token = extractToken(raw);
    if (!token) {
      setError("That does not look like an AttendX attendance link or token. Scan the current QR from your teacher's screen.");
      return;
    }
    setError(null);
    router.push(`/attend/${encodeURIComponent(token)}`);
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    go(manual);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Scan attendance"
        title="Check in to the current session"
        description="Scan the QR shown by your teacher. The QR opens the official AttendX URL and never marks you present on its own."
      />

      <Card>
        <CardHeader title="In-browser scanner" description="Requires camera permission on this page." />
        <div className="p-4">
          <QrScanner onResult={go} />
        </div>
      </Card>

      {error ? (
        <div className="mt-4">
          <Alert tone="danger">{error}</Alert>
        </div>
      ) : null}

      <Card className="mt-4">
        <CardHeader title="Use your phone's native camera" />
        <div className="space-y-3 p-5 text-sm text-[#475467]">
          <p className="flex items-start gap-2">
            <Smartphone size={16} className="mt-0.5 shrink-0 text-brand" />
            Open your phone camera, point it at the QR on the teacher&apos;s screen, and tap the
            AttendX link that appears. It opens this same verified check-in flow.
          </p>
          <p className="flex items-start gap-2">
            <ShieldCheck size={16} className="mt-0.5 shrink-0 text-brand" />
            Only links on the official AttendX origin are accepted. A screenshot of an old QR will
            fail once its short-lived token expires.
          </p>
        </div>
      </Card>

      <Card className="mt-4">
        <CardHeader title="Paste a session link" description="Useful when camera access is blocked." />
        <form onSubmit={onSubmit} className="space-y-3 p-5">
          <Field
            label="Attendance link or token"
            hint="Paste the full link from the teacher's QR, or the token value."
          >
            <Input
              value={manual}
              onChange={(event) => setManual(event.target.value)}
              placeholder="https://your-attendx-host/attend/…"
              autoCapitalize="off"
              autoCorrect="off"
            />
          </Field>
          <Button type="submit" className="w-full">
            <KeyRound size={16} /> Validate session link
          </Button>
        </form>
      </Card>

      <div className="mt-4 rounded-xl border border-line bg-white p-4 text-xs leading-relaxed text-muted">
        <p className="flex items-center gap-2 font-semibold text-ink">
          <QrCode size={15} /> What happens next
        </p>
        <ol className="mt-2 list-decimal space-y-1 pl-5">
          <li>The session and your enrolment are checked by the server.</li>
          <li>Enter the temporary PIN, then complete the requested verification steps.</li>
          <li>You see an explicit result and, for accepted attendance, a unique reference.</li>
        </ol>
        <p className="mt-2 flex items-center gap-1 text-brand">
          Continue to check-in <ArrowRight size={13} />
        </p>
      </div>
    </div>
  );
}
