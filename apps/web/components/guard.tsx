"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ShieldAlert } from "lucide-react";
import { useEffect, type ReactNode } from "react";
import { homeForRole, useAuth } from "@/components/auth-provider";
import { Card, Spinner } from "@/components/ui";
import type { Role } from "@/lib/types";

export function RequireRole({ roles, children }: { roles: Role[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
    }
  }, [loading, user, router, pathname]);

  if (loading) {
    return (
      <div className="min-h-screen bg-workspace">
        <Spinner label="Loading your workspace" />
      </div>
    );
  }
  if (!user) return null;
  if (!roles.includes(user.role)) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-workspace p-4">
        <Card className="max-w-md p-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-[#FEF3F2] text-danger">
            <ShieldAlert size={22} />
          </div>
          <h1 className="text-lg font-semibold text-ink">This area is not available to your role</h1>
          <p className="mt-1 text-sm text-muted">
            You are signed in as a {user.role}. AttendX keeps sensitive verification and
            administration tools separated by role.
          </p>
          <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
            <Link
              href={homeForRole(user.role)}
              className="inline-flex h-10 items-center justify-center rounded-lg bg-brand px-4 text-sm font-semibold text-white hover:bg-brand-hover"
            >
              Go to my workspace
            </Link>
            <Link href="/" className="text-sm text-brand hover:underline">
              Back to home
            </Link>
          </div>
        </Card>
      </div>
    );
  }
  return <>{children}</>;
}
