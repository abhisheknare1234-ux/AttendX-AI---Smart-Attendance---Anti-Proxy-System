"use client";

import {
  BookOpen,
  Building2,
  ClipboardList,
  Fingerprint,
  GraduationCap,
  LayoutDashboard,
  MapPinned,
  ScrollText,
  ServerCog,
  ShieldAlert,
  SlidersHorizontal,
  UserCog,
  UserRound,
  UsersRound,
} from "lucide-react";
import type { ReactNode } from "react";
import { RequireRole } from "@/components/guard";
import { DashboardShell, type NavItem } from "@/components/shell";

export const adminNav: NavItem[] = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/admin/users", label: "Users", icon: UserCog },
  { href: "/admin/students", label: "Students", icon: GraduationCap },
  { href: "/admin/teachers", label: "Teachers", icon: UsersRound },
  { href: "/admin/classes", label: "Classes", icon: Building2 },
  { href: "/admin/subjects", label: "Subjects", icon: BookOpen },
  { href: "/admin/enrollments", label: "Enrollments", icon: UserRound },
  { href: "/admin/assignments", label: "Teacher assignments", icon: ClipboardList },
  { href: "/admin/classrooms", label: "Classrooms", icon: MapPinned },
  { href: "/admin/geofences", label: "Geofences", icon: Fingerprint },
  { href: "/admin/policies", label: "Attendance policies", icon: SlidersHorizontal },
  { href: "/admin/verification", label: "Verification services", icon: ServerCog },
  { href: "/admin/reports", label: "Attendance reports", icon: ScrollText },
  { href: "/admin/audit", label: "Audit logs", icon: ScrollText },
  { href: "/admin/security", label: "Security", icon: ShieldAlert },
  { href: "/admin/health", label: "System health", icon: ServerCog },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={["admin"]}>
      <DashboardShell nav={adminNav} roleLabel="Administrator">
        {children}
      </DashboardShell>
    </RequireRole>
  );
}
