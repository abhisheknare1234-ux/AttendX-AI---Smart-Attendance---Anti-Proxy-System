"use client";

import {
  BookOpen,
  CalendarClock,
  ClipboardCheck,
  GraduationCap,
  LayoutDashboard,
  ListChecks,
  PlayCircle,
  ScrollText,
  UserRound,
  UsersRound,
} from "lucide-react";
import type { ReactNode } from "react";
import { RequireRole } from "@/components/guard";
import { DashboardShell, type NavItem } from "@/components/shell";

export const teacherNav: NavItem[] = [
  { href: "/teacher", label: "Overview", icon: LayoutDashboard, exact: true },
  { href: "/teacher/classes", label: "My classes", icon: BookOpen },
  { href: "/teacher/subjects", label: "My subjects", icon: GraduationCap },
  { href: "/teacher/students", label: "My students", icon: UsersRound },
  { href: "/teacher/sessions/new", label: "Start attendance", icon: PlayCircle },
  { href: "/teacher/sessions", label: "Attendance sessions", icon: CalendarClock },
  { href: "/teacher/reviews", label: "Review queue", icon: ListChecks },
  { href: "/teacher/reports", label: "Reports", icon: ScrollText },
  { href: "/teacher/profile", label: "Profile", icon: UserRound },
];

export default function TeacherLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={["teacher"]}>
      <DashboardShell nav={teacherNav} roleLabel="Teacher">
        {children}
      </DashboardShell>
    </RequireRole>
  );
}
