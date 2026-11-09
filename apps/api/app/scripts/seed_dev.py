"""Development-only synthetic demo data.

This script refuses to run outside APP_ENV=development. It creates no attendance
records and must never be used to populate a production database.
"""
from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal, create_all
from app.models import (
    AttendancePolicy,
    ClassEnrollment,
    Classroom,
    SchoolClass,
    StudentProfile,
    Subject,
    TeacherAssignment,
    TeacherProfile,
    User,
    UserRole,
)
from app.services.auth import bootstrap_admin
from app.services.users import provision_student, provision_teacher


def _get_or_create_class(db, *, code: str, name: str, department: str, year: int, division: str):
    existing = db.scalar(select(SchoolClass).where(SchoolClass.code == code))
    if existing:
        return existing
    item = SchoolClass(
        code=code, name=name, department=department, year=year, division=division
    )
    db.add(item)
    db.flush()
    return item


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed a development demo dataset")
    parser.add_argument("--admin-email", default="admin@attendx.dev")
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--teacher-email", default="teacher@attendx.dev")
    parser.add_argument("--teacher-password", required=True)
    parser.add_argument("--student-password", required=True)
    parser.add_argument("--students", type=int, default=8)
    args = parser.parse_args()

    settings = get_settings()
    if settings.app_env != "development":
        print("Refusing: seed_dev is only allowed when APP_ENV=development.", file=sys.stderr)
        return 2

    create_all()
    with SessionLocal() as db:
        existing_admin = db.scalar(select(User).where(User.email == args.admin_email.lower()))
        if existing_admin is None:
            admin = bootstrap_admin(
                db,
                email=args.admin_email,
                password=args.admin_password,
                full_name="Demo Administrator",
            )
        else:
            admin = existing_admin

        teacher = db.scalar(select(User).where(User.email == args.teacher_email.lower()))
        if teacher is None:
            teacher, _ = provision_teacher(
                db,
                actor_user_id=admin.id,
                email=args.teacher_email,
                full_name="Demo Teacher",
                password=args.teacher_password,
                employee_id="DEMO-EMP-001",
                department="Computer Engineering",
                designation="Assistant Professor",
            )
        teacher_profile = db.scalar(
            select(TeacherProfile).where(TeacherProfile.user_id == teacher.id)
        )

        school_class = _get_or_create_class(
            db,
            code="DEMO-CE-3A",
            name="Demo TE Computer A",
            department="Computer Engineering",
            year=3,
            division="A",
        )
        subject = db.scalar(select(Subject).where(Subject.code == "DEMO-DBMS"))
        if subject is None:
            subject = Subject(
                code="DEMO-DBMS",
                name="Database Management Systems (demo)",
                class_id=school_class.id,
            )
            db.add(subject)
            db.flush()

        classroom = db.scalar(select(Classroom).where(Classroom.code == "DEMO-R101"))
        if classroom is None:
            classroom = Classroom(
                code="DEMO-R101",
                name="Demo Classroom 101",
                building="Demo Block",
                latitude=18.5204,
                longitude=73.8567,
                default_radius_m=80.0,
                max_accuracy_m=100.0,
            )
            db.add(classroom)
            db.flush()

        policy = db.scalar(select(AttendancePolicy).where(AttendancePolicy.name == "Demo default policy"))
        if policy is None:
            policy = AttendancePolicy(name="Demo default policy", is_default=True)
            db.add(policy)
            db.flush()

        assignment = db.scalar(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == teacher_profile.id,
                TeacherAssignment.class_id == school_class.id,
                TeacherAssignment.subject_id == subject.id,
            )
        )
        if assignment is None:
            db.add(
                TeacherAssignment(
                    teacher_id=teacher_profile.id,
                    class_id=school_class.id,
                    subject_id=subject.id,
                )
            )

        created_students: list[User] = []
        for index in range(1, args.students + 1):
            email = f"student{index}@attendx.dev"
            student = db.scalar(select(User).where(User.email == email))
            if student is not None:
                created_students.append(student)
                continue
            student, _ = provision_student(
                db,
                actor_user_id=admin.id,
                email=email,
                full_name=f"Demo Student {index}",
                password=args.student_password,
                roll_number=f"DEMO-ROLL-{index:03d}",
                department="Computer Engineering",
                programme="B.E.",
                year=3,
                division="A",
                batch=None,
                admission_year=2023,
            )
            created_students.append(student)

        for student in created_students:
            profile = db.scalar(
                select(StudentProfile).where(StudentProfile.user_id == student.id)
            )
            if profile is None:
                continue
            enrolled = db.scalar(
                select(ClassEnrollment).where(
                    ClassEnrollment.class_id == school_class.id,
                    ClassEnrollment.student_id == profile.id,
                )
            )
            if enrolled is None:
                db.add(ClassEnrollment(class_id=school_class.id, student_id=profile.id))

        db.commit()

    print("Development demo data ready (no attendance records created).")
    print(f"Administrator: {args.admin_email}")
    print(f"Teacher:       {args.teacher_email}")
    print(f"Students:      student1..student{args.students}@attendx.dev")
    print("Passwords are the values supplied on the command line.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
