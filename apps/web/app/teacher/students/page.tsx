"use client";

import { UsersRound } from "lucide-react";
import { Card, EmptyState, PageHeader, Skeleton, Table, TableWrap, Td, Th } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";

interface StudentRow {
  student_id: string;
  name: string;
  roll_number: string;
  class_id: string;
  class_name: string;
}

export default function TeacherStudentsPage() {
  const students = useApiData<StudentRow[]>("/teacher/students");
  return (
    <div>
      <PageHeader
        eyebrow="My students"
        title="Students in your assigned classes"
        description="Distinct enrolled students across your teaching assignments. No fabricated roster is used."
      />
      <Card>
        {students.loading ? (
          <div className="p-4">
            <Skeleton className="h-40" />
          </div>
        ) : !students.data?.length ? (
          <EmptyState
            icon={<UsersRound size={20} />}
            title="No students enrolled"
            description="Students appear once an administrator enrols them in your assigned classes."
          />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Student</Th>
                  <Th>Roll number</Th>
                  <Th>Class</Th>
                </tr>
              </thead>
              <tbody>
                {students.data.map((row) => (
                  <tr key={row.student_id}>
                    <Td className="font-medium text-ink">{row.name}</Td>
                    <Td className="text-muted">{row.roll_number}</Td>
                    <Td className="text-muted">{row.class_name}</Td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </TableWrap>
        )}
      </Card>
    </div>
  );
}
