"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { KeyRound, ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";
import { homeForRole, useAuth } from "@/components/auth-provider";
import { RequireRole } from "@/components/guard";
import { Alert, Button, Card, CardHeader, Field, Input, PageHeader } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";

export default function AccountPasswordPage() {
  return (
    <RequireRole roles={["admin", "teacher", "student"]}>
      <PasswordContent />
    </RequireRole>
  );
}

function PasswordContent() {
  const { user, refresh } = useAuth();
  const router = useRouter();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (next !== confirm) {
      setError("The new password confirmation does not match.");
      return;
    }
    setBusy(true);
    try {
      await api("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      setDone(true);
      await refresh();
      if (user) {
        window.setTimeout(() => router.replace(homeForRole(user.role)), 1200);
      }
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen bg-workspace px-4 py-10">
      <div className="mx-auto max-w-lg">
        <div className="mb-6 flex items-center justify-between">
          <Link href={user ? homeForRole(user.role) : "/"} className="flex items-center gap-2">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white">
              <ShieldCheck size={19} />
            </span>
            <span className="text-base font-bold text-ink">
              AttendX <span className="text-brand">AI</span>
            </span>
          </Link>
          {user ? (
            <Link href={homeForRole(user.role)} className="text-xs font-medium text-muted hover:text-brand">
              Back to workspace
            </Link>
          ) : null}
        </div>

        <PageHeader
          eyebrow="Account security"
          title="Change your password"
          description="Passwords are hashed with Argon2id. Your current session stays active after the change."
        />

        <Card>
          <CardHeader title="Password update" action={<KeyRound size={16} className="text-muted" />} />
          <form onSubmit={submit} className="space-y-4 p-5">
            {done ? (
              <Alert tone="success" title="Password changed">
                Your new password is active. Redirecting to your workspace…
              </Alert>
            ) : null}
            {error ? <Alert tone="danger">{error}</Alert> : null}
            <Field label="Current password" required>
              <Input
                type="password"
                autoComplete="current-password"
                value={current}
                onChange={(event) => setCurrent(event.target.value)}
                required
              />
            </Field>
            <Field
              label="New password"
              hint="At least 10 characters, with upper and lower case letters and a digit."
              required
            >
              <Input
                type="password"
                autoComplete="new-password"
                value={next}
                onChange={(event) => setNext(event.target.value)}
                required
                minLength={10}
              />
            </Field>
            <Field label="Confirm new password" required>
              <Input
                type="password"
                autoComplete="new-password"
                value={confirm}
                onChange={(event) => setConfirm(event.target.value)}
                required
              />
            </Field>
            <Button type="submit" className="w-full" loading={busy} disabled={done}>
              Update password
            </Button>
            <p className="text-[11px] leading-relaxed text-muted">
              Never share your password. AttendX staff will not ask for it. If you believe your
              account is compromised, contact your institution administrator so the session can be
              revoked.
            </p>
          </form>
        </Card>
      </div>
    </div>
  );
}
