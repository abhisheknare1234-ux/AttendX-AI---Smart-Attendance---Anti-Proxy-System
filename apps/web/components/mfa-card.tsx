"use client";

import { KeyRound, ShieldCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/components/auth-provider";
import { QrSvg } from "@/components/qr";
import {
  Alert,
  Badge,
  Button,
  Card,
  CardHeader,
  Field,
  Input,
  Skeleton,
} from "@/components/ui";
import { api, errorMessage, formatDateTime } from "@/lib/api";
import type { MfaSetup, MfaStatus } from "@/lib/types";

export function MfaCard() {
  const { user, refresh } = useAuth();
  const [status, setStatus] = useState<MfaStatus | null>(null);
  const [setup, setSetup] = useState<MfaSetup | null>(null);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  async function load() {
    try {
      setStatus(await api<MfaStatus>("/auth/mfa"));
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function beginSetup() {
    setBusy("setup");
    setError(null);
    setMessage(null);
    try {
      const result = await api<MfaSetup>("/auth/mfa/setup", { method: "POST" });
      setSetup(result);
      setCode("");
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function enable(event: FormEvent) {
    event.preventDefault();
    setBusy("enable");
    setError(null);
    try {
      setStatus(
        await api<MfaStatus>("/auth/mfa/enable", {
          method: "POST",
          body: JSON.stringify({ code: code.trim() }),
        }),
      );
      setSetup(null);
      setCode("");
      setMessage("Authenticator MFA is enabled. Future sign-ins require a code.");
      await refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  async function disable(event: FormEvent) {
    event.preventDefault();
    setBusy("disable");
    setError(null);
    try {
      setStatus(
        await api<MfaStatus>("/auth/mfa/disable", {
          method: "POST",
          body: JSON.stringify({ password, code: code.trim() }),
        }),
      );
      setPassword("");
      setCode("");
      setMessage("MFA disabled. Other sessions were revoked.");
      await refresh();
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card>
      <CardHeader
        title="Authenticator app (MFA)"
        description="Time-based one-time codes add a second factor to password sign-in."
        action={<ShieldCheck size={16} className="text-muted" />}
      />
      <div className="space-y-3 p-5">
        {!status ? (
          <Skeleton className="h-20" />
        ) : (
          <>
            <div className="flex items-center justify-between">
              <span className="text-xs text-muted">Status</span>
              <Badge tone={status.enabled ? "green" : "neutral"}>
                {status.enabled ? "Enabled" : status.pending_setup ? "Setup pending" : "Not enabled"}
              </Badge>
            </div>
            {status.enabled ? (
              <p className="text-[11px] text-muted">
                Enabled {formatDateTime(status.enrolled_at)}. Disabling requires your password and
                a current code; other sessions are revoked.
              </p>
            ) : null}

            {!status.enabled && !setup ? (
              <Button onClick={() => void beginSetup()} loading={busy === "setup"}>
                <KeyRound size={15} /> Set up authenticator
              </Button>
            ) : null}

            {setup ? (
              <form onSubmit={enable} className="space-y-3">
                <div className="rounded-lg border border-line bg-[#FAFBFD] p-3">
                  <p className="text-xs font-semibold text-ink">
                    Scan this URI with your authenticator app
                  </p>
                  <div className="mt-2 flex justify-center">
                    <QrSvg value={setup.otpauth_uri} size={160} />
                  </div>
                  <p className="mt-2 text-center text-[10px] text-muted">
                    Manual secret:{" "}
                    <code className="break-all font-mono text-ink">{setup.secret}</code>
                  </p>
                </div>
                <Field label="6-digit code from the app" required>
                  <Input
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 10))}
                    required
                    className="text-center font-mono tracking-[0.25em]"
                  />
                </Field>
                <Button type="submit" loading={busy === "enable"} disabled={code.length < 6}>
                  Enable MFA
                </Button>
              </form>
            ) : null}

            {status.enabled ? (
              <form onSubmit={disable} className="space-y-3 border-t border-line pt-3">
                <Field label="Password to disable MFA" required>
                  <Input
                    type="password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                </Field>
                <Field label="Current authenticator code" required>
                  <Input
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 10))}
                    required
                  />
                </Field>
                <Button
                  type="submit"
                  variant="secondary"
                  loading={busy === "disable"}
                  disabled={!password || code.length < 6}
                >
                  Disable MFA
                </Button>
              </form>
            ) : null}
          </>
        )}
        {message ? <Alert tone="success">{message}</Alert> : null}
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <p className="text-[10px] leading-relaxed text-muted">
          MFA secrets are encrypted at rest. There is no email recovery flow: if you lose your
          authenticator, an administrator must disable MFA for your account and issue a password
          reset token.
        </p>
      </div>
    </Card>
  );
}
