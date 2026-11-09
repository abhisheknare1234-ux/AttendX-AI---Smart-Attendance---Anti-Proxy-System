"use client";

import { BookOpen } from "lucide-react";
import { Card, EmptyState, PageHeader, Skeleton, Table, TableWrap, Td, Th } from "@/components/ui";
import { useApiData } from "@/hooks/use-api-data";

interface ClassRow {
  id: string;
  code: string;
  name: string;
  department: string;
  year: number;
  division: string;
  subjects: number;
  students: number;
}

export default function TeacherClassesPage() {
  const classes = useApiData<ClassRow[]>("/teacher/classes");
  return (
    <div>
      <PageHeader
        eyebrow="My classes"
        title="Classes assigned to you"
        description="Derived from active teaching assignments. Students are counted from verified class enrolments."
      />
      <Card>
        {classes.loading ? (
          <div className="p-4">
            <Skeleton className="h-40" />
          </div>
        ) : !classes.data?.length ? (
          <EmptyState
            icon={<BookOpen size={20} />}
            title="No assigned classes"
            description="An administrator must create a teaching assignment before you can open an attendance session."
          />
        ) : (
          <TableWrap>
            <Table>
              <thead>
                <tr>
                  <Th>Class</Th>
                  <Th>Department</Th>
                  <Th>Year / division</Th>
                  <Th>Subjects</Th>
                  <Th>Students</Th>
                </tr>
              </thead>
              <tbody>
                {classes.data.map((row) => (
                  <tr key={row.id}>
                    <Td>
                      <p className="font-medium text-ink">{row.name}</p>
                      <p className="text-[11px] text-muted">{row.code}</p>
                    </Td>
                    <Td className="text-muted">{row.department}</Td>
                    <Td className="text-muted">
                      {row.year} / {row.division}
                    </Td>
                    <Td className="text-muted">{row.subjects}</Td>
                    <Td className="font-medium text-ink">{row.students}</Td>
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
