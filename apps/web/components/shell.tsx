"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ChevronRight,
  LogOut,
  Menu,
  ShieldCheck,
  X,
  type LucideIcon,
} from "lucide-react";
import { useState, type ReactNode } from "react";
import { useAuth } from "@/components/auth-provider";
import { cn } from "@/components/ui";

export interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="flex items-center gap-2.5" aria-label="AttendX AI home">
      <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-white shadow-sm">
        <ShieldCheck size={20} strokeWidth={2.2} />
      </span>
      {!compact ? (
        <span className="leading-tight">
          <span className="block text-[15px] font-bold tracking-tight text-ink">
            AttendX <span className="text-brand">AI</span>
          </span>
          <span className="block text-[10px] font-medium uppercase tracking-[0.12em] text-muted">
            Verified attendance
          </span>
        </span>
      ) : null}
    </Link>
  );
}

function isActive(pathname: string, item: NavItem): boolean {
  if (item.exact) return pathname === item.href;
  return pathname === item.href || pathname.startsWith(`${item.href}/`);
}

function NavLinks({
  nav,
  onNavigate,
}: {
  nav: NavItem[];
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto px-3 py-3">
      {nav.map((item) => {
        const active = isActive(pathname, item);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={active ? "page" : undefined}
            className={cn(
              "group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
              active
                ? "bg-active text-brand"
                : "text-[#475467] hover:bg-workspace hover:text-ink",
            )}
          >
            <Icon
              size={17}
              strokeWidth={active ? 2.2 : 1.9}
              className={cn(active ? "text-brand" : "text-muted group-hover:text-ink")}
            />
            <span className="flex-1">{item.label}</span>
            {active ? <ChevronRight size={14} className="text-brand/70" /> : null}
          </Link>
        );
      })}
    </nav>
  );
}

function AccountFooter() {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="border-t border-line p-3">
      <div className="mb-2 flex items-center gap-2.5 rounded-lg px-2 py-1.5">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-active text-xs font-bold text-brand">
          {user.full_name
            .split(" ")
            .slice(0, 2)
            .map((part) => part[0])
            .join("")
            .toUpperCase()}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-xs font-semibold text-ink">{user.full_name}</span>
          <span className="block truncate text-[11px] capitalize text-muted">{user.role}</span>
        </span>
      </div>
      <div className="flex items-center justify-between gap-2 px-1">
        <Link
          href="/account/password"
          className="text-[11px] font-medium text-muted hover:text-brand"
        >
          Account security
        </Link>
        <button
          type="button"
          onClick={() => void logout()}
          className="inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-[11px] font-medium text-muted hover:bg-workspace hover:text-danger"
        >
          <LogOut size={13} /> Sign out
        </button>
      </div>
    </div>
  );
}

export function DashboardShell({
  nav,
  roleLabel,
  children,
}: {
  nav: NavItem[];
  roleLabel: string;
  children: ReactNode;
}) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();
  const { user } = useAuth();
  const current = nav.find((item) => isActive(pathname, item));

  return (
    <div className="min-h-screen bg-workspace">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[260px] flex-col border-r border-line bg-white lg:flex">
        <div className="flex h-16 items-center border-b border-line px-5">
          <Brand />
        </div>
        <div className="px-5 pt-4">
          <span className="inline-flex rounded-full bg-workspace px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-muted">
            {roleLabel}
          </span>
        </div>
        <NavLinks nav={nav} />
        <AccountFooter />
      </aside>

      <div className="lg:pl-[260px]">
        <header className="sticky top-0 z-20 flex h-16 items-center justify-between gap-3 border-b border-line bg-white/95 px-4 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="rounded-lg border border-line p-2 text-muted hover:bg-workspace lg:hidden"
              aria-label="Open navigation"
            >
              <Menu size={18} />
            </button>
            <div className="hidden lg:block">
              <p className="text-[11px] font-medium text-muted">{roleLabel} workspace</p>
              <p className="truncate text-sm font-semibold text-ink">{current?.label ?? "Overview"}</p>
            </div>
            <div className="lg:hidden">
              <Brand compact />
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden max-w-[220px] truncate text-xs text-muted sm:block">
              {user?.email}
            </span>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-active text-[11px] font-bold text-brand">
              {user?.full_name?.slice(0, 1).toUpperCase() ?? "A"}
            </span>
          </div>
        </header>

        {user?.must_change_password ? (
          <div className="border-b border-[#FEDF89] bg-[#FFFAEB] px-4 py-2 text-xs text-[#7A3D06] sm:px-6">
            You are using a temporary password.{" "}
            <Link href="/account/password" className="font-semibold underline">
              Set a permanent password
            </Link>{" "}
            before continuing normal use.
          </div>
        ) : null}

        <main className="mx-auto max-w-[1400px] px-4 py-6 sm:px-6 lg:py-8">{children}</main>
      </div>

      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-[#101828]/50"
            aria-hidden
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative flex h-full w-[280px] flex-col bg-white shadow-xl">
            <div className="flex h-16 items-center justify-between border-b border-line px-4">
              <Brand />
              <button
                type="button"
                onClick={() => setMobileOpen(false)}
                className="rounded-lg p-1.5 text-muted hover:bg-workspace"
                aria-label="Close navigation"
              >
                <X size={18} />
              </button>
            </div>
            <NavLinks nav={nav} onNavigate={() => setMobileOpen(false)} />
            <AccountFooter />
          </aside>
        </div>
      ) : null}
    </div>
  );
}

export function StudentShell({
  nav,
  children,
}: {
  nav: NavItem[];
  children: ReactNode;
}) {
  const pathname = usePathname();
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-workspace">
      <header className="sticky top-0 z-20 border-b border-line bg-white/95 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-xl items-center justify-between">
          <Brand />
          <div className="flex items-center gap-2">
            <span className="hidden text-[11px] text-muted xs:block">{user?.full_name}</span>
            <button
              type="button"
              onClick={() => void logout()}
              className="rounded-lg p-2 text-muted hover:bg-workspace hover:text-danger"
              aria-label="Sign out"
            >
              <LogOut size={17} />
            </button>
          </div>
        </div>
      </header>

      {user?.must_change_password ? (
        <div className="border-b border-[#FEDF89] bg-[#FFFAEB] px-4 py-2 text-center text-[11px] text-[#7A3D06]">
          Temporary password in use.{" "}
          <Link href="/account/password" className="font-semibold underline">
            Change it now
          </Link>
        </div>
      ) : null}

      <main className="mobile-safe-bottom mx-auto max-w-xl px-4 py-4">{children}</main>

      <nav
        className="fixed inset-x-0 bottom-0 z-20 border-t border-line bg-white/98 pb-[env(safe-area-inset-bottom)] backdrop-blur"
        aria-label="Student navigation"
      >
        <div className="mx-auto grid max-w-xl grid-cols-5">
          {nav.map((item) => {
            const active = isActive(pathname, item);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center gap-1 py-2.5 text-[10px] font-semibold",
                  active ? "text-brand" : "text-muted",
                )}
              >
                <span
                  className={cn(
                    "flex h-8 w-12 items-center justify-center rounded-full",
                    active ? "bg-active" : "",
                  )}
                >
                  <Icon size={18} strokeWidth={active ? 2.3 : 1.9} />
                </span>
                {item.label}
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

export function PublicHeader() {
  return (
    <header className="sticky top-0 z-30 border-b border-line bg-white/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Brand />
        <nav className="hidden items-center gap-6 text-sm text-[#475467] md:flex">
          <a href="/#product" className="hover:text-brand">
            Product
          </a>
          <a href="/#security" className="hover:text-brand">
            Security
          </a>
          <a href="/#privacy" className="hover:text-brand">
            Privacy
          </a>
          <a href="/#technology" className="hover:text-brand">
            Technology
          </a>
        </nav>
        <div className="flex items-center gap-2">
          <Link
            href="/login"
            className="rounded-lg px-3 py-2 text-sm font-semibold text-ink hover:bg-workspace"
          >
            Sign in
          </Link>
          <a
            href="mailto:pilot@attendx.example?subject=AttendX%20AI%20institutional%20pilot%20request"
            className="hidden rounded-lg bg-brand px-3 py-2 text-sm font-semibold text-white hover:bg-brand-hover sm:block"
          >
            Request a pilot
          </a>
        </div>
      </div>
    </header>
  );
}

export function BrandFooter() {
  return (
    <footer className="border-t border-line bg-white">
      <div className="mx-auto grid max-w-7xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-4">
        <div className="md:col-span-2">
          <Brand />
          <p className="mt-3 max-w-sm text-sm leading-relaxed text-muted">
            Intelligent attendance with multi-factor verification and explainable trust.
            Designed for institutional pilots, not as a replacement for an academic ERP.
          </p>
          <p className="mt-4 text-xs text-muted">
            AttendX AI is an independent project. Institutional deployment requires authorization,
            privacy review and a signed pilot agreement.
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink">Product</p>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>
              <a href="/#how-it-works" className="hover:text-brand">
                How it works
              </a>
            </li>
            <li>
              <a href="/#verification" className="hover:text-brand">
                Verification factors
              </a>
            </li>
            <li>
              <a href="/#interfaces" className="hover:text-brand">
                Desktop and mobile
              </a>
            </li>
            <li>
              <a href="/#limitations" className="hover:text-brand">
                Current limitations
              </a>
            </li>
          </ul>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink">Institution</p>
          <ul className="mt-3 space-y-2 text-sm text-muted">
            <li>
              <a href="mailto:pilot@attendx.example" className="hover:text-brand">
                Request a pilot
              </a>
            </li>
            <li>
              <a href="/login" className="hover:text-brand">
                Authorized sign in
              </a>
            </li>
            <li>Pune, Maharashtra, India</li>
          </ul>
        </div>
      </div>
      <div className="border-t border-line px-4 py-4 text-center text-[11px] text-muted sm:px-6">
        © {new Date().getFullYear()} AttendX AI. Product demonstration build. No institutional
        adoption is implied.
      </div>
    </footer>
  );
}
