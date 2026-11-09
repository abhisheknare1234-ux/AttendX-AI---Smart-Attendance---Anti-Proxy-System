"use client";

import { GraduationCap } from "lucide-react";
import { Card, EmptyState, PageHeader, Skeleton, Table, TableWrap, Td, Th } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";

interface SubjectRow {
  assignment_id: string;
  class_id: string;
  class_name: string;
  class_code: string;
  subject_id: string | null;
  subject_name: string;
  subject_code: string | null;
  students: number;
}

export default function TeacherSubjectsPage() {
  const subjects = useApiData<SubjectRow[]>("/teacher/subjects");
  return (
    <div>
      <PageHeader
        eyebrow="My subjects"
        title="Teaching assignments"
        description="Each row is an active assignment. Sessions can only be created for these class and subject pairs."
      />
      <Card>
        {subjects.loading ? (
          <div className="p-4">
            <Skeleton className="h-40" />
          </div>
        ) : !subjects.data?.length ? (
          <EmptyState
            icon={<GraduationCap size={20} />}
            title="No subject assignments"
            description="An administrator can assign you to a class and subject."
          />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Subject</Th>
                  <Th>Class</Th>
                  <Th>Code</Th>
                  <Th>Students</Th>
                </tr>
              </thead>
              <tbody>
                {subjects.data.map((row) => (
                  <tr key={row.assignment_id}>
                    <Td className="font-medium text-ink">{row.subject_name}</Td>
                    <Td className="text-muted">
                      {row.class_name} ({row.class_code})
                    </Td>
                    <Td className="text-muted">{row.subject_code ?? "—"}</Td>
                    <Td className="text-muted">{row.students}</Td>
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
