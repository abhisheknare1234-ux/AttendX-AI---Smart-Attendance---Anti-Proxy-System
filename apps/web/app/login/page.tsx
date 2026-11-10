"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, Lock, Mail, ShieldCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { homeForRole, useAuth } from "@/components/auth-provider";
import { Alert, Button, Field, Input } from "@/components/ui";
import { ApiRequestError } from "@/lib/api";
import type { MfaChallenge, User } from "@/lib/types";

function safeNext(user: User): string {
  if (typeof window === "undefined") return homeForRole(user.role);
  const next = new URLSearchParams(window.location.search).get("next");
  if (
    next &&
    next.startsWith("/") &&
    !next.startsWith("//") &&
    !next.startsWith("/login") &&
    next.length < 500
  ) {
    return next;
  }
  return homeForRole(user.role);
}

export default function LoginPage() {
  const { user, loading, login, verifyMfa } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [code, setCode] = useState("");
  const [mfaChallenge, setMfaChallenge] = useState<MfaChallenge | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && user) {
      router.replace(safeNext(user));
    }
  }, [loading, user, router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const outcome = await login(email.trim(), password);
      if (outcome.kind === "mfa") {
        setMfaChallenge(outcome.challenge);
        setCode("");
        return;
      }
      router.replace(safeNext(outcome.user));
    } catch (caught) {
      if (caught instanceof ApiRequestError) {
        setError(caught.message);
      } else {
        setError("Unable to reach the AttendX service. Check that the API is running and try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function onVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!mfaChallenge) return;
    setError(null);
    setSubmitting(true);
    try {
      const signedIn = await verifyMfa(mfaChallenge.challenge_token, code.trim());
      router.replace(safeNext(signedIn));
    } catch (caught) {
      if (caught instanceof ApiRequestError) {
        setError(caught.message);
      } else {
        setError("Unable to verify the authenticator code. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-screen bg-white lg:grid-cols-[1.05fr_1fr]">
      <section className="relative hidden overflow-hidden bg-brand px-12 py-10 text-white lg:flex lg:flex-col">
        <div className="brand-grid absolute inset-0 opacity-70" aria-hidden />
        <div className="relative">
          <Link href="/" className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-white/15">
              <ShieldCheck size={22} />
            </span>
            <span>
              <span className="block text-lg font-bold tracking-tight">
                AttendX <span className="text-[#BFD3FF]">AI</span>
              </span>
              <span className="block text-[10px] font-medium uppercase tracking-[0.18em] text-[#BFD3FF]">
                Verified attendance
              </span>
            </span>
          </Link>
        </div>

        <div className="relative my-auto max-w-lg py-12">
          <p className="mb-4 inline-flex rounded-full border border-white/25 bg-white/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em]">
            Institutional attendance verification
          </p>
          <h1 className="text-4xl font-semibold leading-[1.12] tracking-tight">
            Attendance that proves presence, not just a tap.
          </h1>
          <p className="mt-4 text-[15px] leading-relaxed text-[#D7E4FF]">
            Rotating session QR codes, temporary PINs, classroom location evidence and
            provider-based face and liveness checks — combined by an explainable risk engine,
            reviewed by the teacher who owns the session.
          </p>

          <div className="mt-8 rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur-sm">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-[#D7E4FF]">
                Verification chain
              </span>
              <span className="rounded-full bg-white/15 px-2 py-0.5 text-[10px] font-semibold">
                Server-authoritative
              </span>
            </div>
            <ol className="space-y-2.5">
              {[
                ["Dynamic QR", "Signed token rotates every 30 seconds"],
                ["Temporary PIN", "Attempt-limited, invalidated on session close"],
                ["Location evidence", "Server-side distance and accuracy checks"],
                ["Identity factors", "Face and liveness only through configured providers"],
                ["Risk decision", "Deterministic reason codes and teacher review"],
              ].map(([title, detail]) => (
                <li key={title} className="flex items-start gap-3">
                  <span className="mt-1 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-white/50 text-[9px]">
                    ✓
                  </span>
                  <span>
                    <span className="block text-sm font-semibold">{title}</span>
                    <span className="block text-[11px] text-[#C9DAFF]">{detail}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <p className="relative text-xs text-[#BFD3FF]">
          Independent attendance product for authorized institutional pilots. Not a complete
          college ERP.
        </p>
      </section>

      <section className="flex flex-col bg-[#F7F9FC] px-5 py-8 sm:px-10 lg:px-16">
        <div className="mb-10 flex items-center justify-between lg:hidden">
          <Link href="/" className="flex items-center gap-2 text-ink">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white">
              <ShieldCheck size={19} />
            </span>
            <span className="text-base font-bold">
              AttendX <span className="text-brand">AI</span>
            </span>
          </Link>
          <Link href="/" className="text-xs font-medium text-muted hover:text-brand">
            Back to home
          </Link>
        </div>

        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center">
          <div className="mb-6">
            <h2 className="text-2xl font-semibold tracking-tight text-ink">
              {mfaChallenge ? "Two-factor verification" : "Sign in to your workspace"}
            </h2>
            <p className="mt-1.5 text-sm text-muted">
              {mfaChallenge
                ? "Enter the current 6-digit code from your authenticator app to finish signing in."
                : "Use the account provisioned by your institution. Student, teacher and administrator roles share one secure backend."}
            </p>
          </div>

          <div className="rounded-2xl border border-line bg-white p-6 shadow-[0_12px_32px_rgba(16,24,40,0.06)]">
            {error ? (
              <div className="mb-4">
                <Alert tone="danger" title={mfaChallenge ? "Verification failed" : "Sign-in failed"}>
                  {error}
                </Alert>
              </div>
            ) : null}

            {mfaChallenge ? (
              <form onSubmit={onVerify} className="space-y-4" noValidate>
                <Field label="Authenticator code" htmlFor="mfa-code" required>
                  <Input
                    id="mfa-code"
                    data-testid="mfa-code"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    maxLength={10}
                    placeholder="000000"
                    className="text-center font-mono text-xl tracking-[0.3em]"
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 10))}
                    required
                  />
                </Field>
                <Button type="submit" loading={submitting} className="w-full" size="lg">
                  Verify code <ArrowRight size={16} />
                </Button>
                <button
                  type="button"
                  onClick={() => {
                    setMfaChallenge(null);
                    setCode("");
                    setError(null);
                  }}
                  className="w-full text-xs font-medium text-muted hover:text-brand"
                >
                  Use a different account
                </button>
              </form>
            ) : (
            <form onSubmit={onSubmit} className="space-y-4" noValidate>
              <Field label="Institutional email" htmlFor="email" required>
                <div className="relative">
                  <Mail
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  />
                  <Input
                    id="email"
                    name="email"
                    type="email"
                    autoComplete="username"
                    inputMode="email"
                    placeholder="name@institution.ac.in"
                    className="pl-9"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                </div>
              </Field>

              <Field label="Password" htmlFor="password" required>
                <div className="relative">
                  <Lock
                    size={16}
                    className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"
                  />
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="Enter your password"
                    className="pl-9 pr-11"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((value) => !value)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-muted hover:bg-workspace hover:text-ink"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </Field>

              <Button type="submit" loading={submitting} className="w-full" size="lg">
                Sign in <ArrowRight size={16} />
              </Button>
            </form>
            )}

            <div className="mt-5 border-t border-line pt-4 text-center">
              {mfaChallenge ? (
                <p className="text-xs leading-relaxed text-muted">
                  Codes come from the authenticator app registered to your account. If you have
                  lost access, ask an administrator to disable MFA and issue a new enrollment.
                </p>
              ) : (
                <>
                  <p className="text-xs leading-relaxed text-muted">
                    There is no public registration. Accounts are created by an administrator, and
                    teachers can only open sessions for classes they are assigned to.
                  </p>
                  <Link
                    href="/reset-password"
                    className="mt-2 inline-block text-xs font-semibold text-brand hover:underline"
                  >
                    Have a password reset token?
                  </Link>
                </>
              )}
            </div>
          </div>

          <p className="mt-5 text-center text-[11px] leading-relaxed text-muted">
            By signing in you acknowledge that attendance verification may process authorized
            account, location and biometric evidence under your institution&apos;s policy. See the{" "}
            <Link href="/#privacy" className="font-medium text-brand hover:underline">
              privacy overview
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  );
}
