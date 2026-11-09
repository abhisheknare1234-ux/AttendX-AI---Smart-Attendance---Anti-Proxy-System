"use client";

import { CalendarClock, Home, ListChecks, QrCode, ScanLine, UserRound } from "lucide-react";
import type { ReactNode } from "react";
import { RequireRole } from "@/components/guard";
import { StudentShell, type NavItem } from "@/components/shell";

export const studentNav: NavItem[] = [
  { href: "/student", label: "Home", icon: Home, exact: true },
  { href: "/student/scan", label: "Scan", icon: QrCode },
  { href: "/student/attendance", label: "History", icon: CalendarClock },
  { href: "/student/subjects", label: "Subjects", icon: ListChecks },
  { href: "/student/profile", label: "Profile", icon: UserRound },
];

export default function StudentLayout({ children }: { children: ReactNode }) {
  return (
    <RequireRole roles={["student"]}>
      <StudentShell nav={studentNav}>{children}</StudentShell>
    </RequireRole>
  );
}
