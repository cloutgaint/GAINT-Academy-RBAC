from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import User, Institution, ParentStudentLink, Record, StudentLocation
from .security import hash_password

DEMO_PASSWORD = "Password@123"

DEMO_USERS = [
    ("admin@gaintacademy.com","GAINT Administrator","Institution Admin"),
    ("teacher@gaintacademy.com","Demo Teacher","Teacher"),
    ("student@gaintacademy.com","Demo Student","Student"),
    ("parent@gaintacademy.com","Demo Parent","Parent / Guardian"),
    ("accounts@gaintacademy.com","Accounts Manager","Accounts"),
    ("hr@gaintacademy.com","HR Manager","HR"),
    ("campus@gaintacademy.com","Campus Administrator","Campus Admin"),
    ("auditor@gaintacademy.com","System Auditor","Auditor"),
]

DEMO_INSTITUTIONS = [
    (1, "GAINT Demo University", "UNIVERSITY", "GAINT-UNI"),
    (2, "GAINT Demo School", "SCHOOL", "GAINT-SCHOOL"),
    (3, "GAINT Demo College", "COLLEGE", "GAINT-COLLEGE"),
]

ROLE_DEFINITIONS = [
    ("admin", "Institution Admin", "Administrator"),
    ("teacher", "Teacher", "Teacher"),
    ("student", "Student", "Student"),
    ("parent", "Parent / Guardian", "Parent"),
    ("accounts", "Accounts", "Accounts Manager"),
    ("hr", "HR", "HR Manager"),
    ("campus", "Campus Admin", "Campus Administrator"),
    ("auditor", "Auditor", "Auditor"),
]

ADAPTIVE_DEMO_TENANTS = [
    ("school", 2, "School"),
    ("college", 3, "College"),
]

def seed(db: Session):
    for institution_id, name, institution_type, code in DEMO_INSTITUTIONS:
        institution = db.get(Institution, institution_id)
        if not institution:
            db.add(Institution(
                id=institution_id, name=name, institution_type=institution_type,
                code=code, is_active=True
            ))
        else:
            institution.name = name
            institution.institution_type = institution_type
            institution.code = code
            institution.is_active = True
    db.commit()

    for email,name,role in DEMO_USERS:
        user = db.scalar(select(User).where(User.email == email))
        if not user:
            db.add(User(
                email=email,name=name,role=role,
                password_hash=hash_password(DEMO_PASSWORD),
                tenant_id=1,campus_id=1,is_active=True
            ))
        else:
            user.name=name
            user.role=role
    db.commit()

    for prefix, tenant_id, institution_label in ADAPTIVE_DEMO_TENANTS:
        for account, role, display_role in ROLE_DEFINITIONS:
            email = f"{prefix}.{account}@gaintacademy.com"
            name = f"GAINT {institution_label} {display_role}"
            user = db.scalar(select(User).where(User.email == email))
            if not user:
                db.add(User(
                    email=email, name=name, role=role,
                    password_hash=hash_password(DEMO_PASSWORD),
                    tenant_id=tenant_id, campus_id=1, is_active=True
                ))
            else:
                user.name = name
                user.role = role
                user.tenant_id = tenant_id
                user.campus_id = 1
                user.is_active = True
    db.commit()

    for prefix, tenant_id, _ in ADAPTIVE_DEMO_TENANTS:
        parent = db.scalar(select(User).where(User.email == f"{prefix}.parent@gaintacademy.com"))
        student = db.scalar(select(User).where(User.email == f"{prefix}.student@gaintacademy.com"))
        if parent and student:
            link = db.scalar(select(ParentStudentLink).where(
                ParentStudentLink.parent_user_id == parent.id,
                ParentStudentLink.student_user_id == student.id,
                ParentStudentLink.tenant_id == tenant_id,
            ))
            if not link:
                db.add(ParentStudentLink(
                    parent_user_id=parent.id,
                    student_user_id=student.id,
                    relationship="Parent",
                    tenant_id=tenant_id,
                ))
    db.commit()

    parent = db.scalar(select(User).where(User.email=="parent@gaintacademy.com"))
    student = db.scalar(select(User).where(User.email=="student@gaintacademy.com"))
    if parent and student:
        link = db.scalar(select(ParentStudentLink).where(
            ParentStudentLink.parent_user_id==parent.id,
            ParentStudentLink.student_user_id==student.id
        ))
        if not link:
            db.add(ParentStudentLink(
                parent_user_id=parent.id,
                student_user_id=student.id,
                relationship="Parent",
                tenant_id=1,
            ))
            db.commit()

    if not db.scalar(select(Record.id).limit(1)):
        data = {
            "Students":["Aarav Sharma","Diya Reddy","Arjun Kumar"],
            "Staff":["Ananya Rao","Rahul Verma"],
            "Transport":["Route A1","Route B2"],
            "Library":["Clean Code","Database Systems"],
            "Admissions":["2026-27 Intake"],
            "Inventory":["Projectors","Tablets"],
        }
        for mod,names in data.items():
            for i,n in enumerate(names):
                db.add(Record(
                    tenant_id=1,campus_id=1,module=mod,name=n,
                    code=f"{mod[:3].upper()}-{1001+i}",
                    category="General",status="Active"
                ))
        db.commit()

    if student and not db.scalar(select(StudentLocation.id).where(StudentLocation.student_user_id==student.id).limit(1)):
        db.add(StudentLocation(
            student_user_id=student.id,
            tenant_id=1,campus_id=1,
            latitude=16.5062,longitude=80.6480,accuracy=8.5,
            source="DEMO",tracking_context="TRANSPORT",status="ACTIVE",
        ))
        db.commit()
