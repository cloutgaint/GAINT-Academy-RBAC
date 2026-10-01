from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models import User

client = TestClient(app)

def test_health():
    r=client.get("/health")
    assert r.status_code==200
    assert r.json()["status"]=="ok"

def test_student_login_and_dashboard():
    r=client.post("/api/v1/auth/login",json={
        "email":"student@gaintacademy.com",
        "password":"Password@123"
    })
    assert r.status_code==200
    token=r.json()["access_token"]
    d=client.get("/api/v1/dashboard",headers={"Authorization":f"Bearer {token}"})
    assert d.status_code==200
    assert d.json()["type"]=="student"

def test_parent_cannot_fetch_random_student():
    r=client.post("/api/v1/auth/login",json={
        "email":"parent@gaintacademy.com","password":"Password@123"
    })
    token=r.json()["access_token"]
    d=client.get("/api/v1/parents/children/999999/location",headers={"Authorization":f"Bearer {token}"})
    assert d.status_code==403


def _login(email,password="Password@123"):
    r=client.post("/api/v1/auth/login",json={"email":email,"password":password})
    assert r.status_code==200
    return {"Authorization":f"Bearer {r.json()['access_token']}"}

def test_student_cannot_access_accounts_finance():
    h=_login("student@gaintacademy.com")
    assert client.get("/api/v1/finance/summary",headers=h).status_code==403
    assert client.get("/api/v1/finance/payments",headers=h).status_code==403

def test_teacher_cannot_manage_fee_ledger():
    h=_login("teacher@gaintacademy.com")
    student=client.post("/api/v1/auth/login",json={"email":"student@gaintacademy.com","password":"Password@123"}).json()["user"]
    r=client.post("/api/v1/fee-ledger",headers=h,json={"student_user_id":student["id"],"fee_code":"NOPE","title":"Unauthorized","amount_due":100})
    assert r.status_code==403

def test_parent_cannot_access_institution_finance_report():
    h=_login("parent@gaintacademy.com")
    assert client.get("/api/v1/finance/report",headers=h).status_code==403

def test_auditor_finance_is_read_only():
    h=_login("auditor@gaintacademy.com")
    assert client.get("/api/v1/finance/summary",headers=h).status_code==200
    student=client.post("/api/v1/auth/login",json={"email":"student@gaintacademy.com","password":"Password@123"}).json()["user"]
    r=client.post("/api/v1/fee-ledger",headers=h,json={"student_user_id":student["id"],"fee_code":"AUDIT","title":"Audit attempt","amount_due":100})
    assert r.status_code==403


def test_student_cannot_open_admin_users_module():
    h=_login("student@gaintacademy.com")
    r=client.get("/api/v1/module-access/Users%20%26%20Roles",headers=h)
    assert r.status_code==403

def test_accounts_cannot_open_hr_recruitment_module():
    h=_login("accounts@gaintacademy.com")
    r=client.get("/api/v1/module-access/Recruitment",headers=h)
    assert r.status_code==403

def test_hr_cannot_open_accounts_payments_module():
    h=_login("hr@gaintacademy.com")
    r=client.get("/api/v1/module-access/Payments",headers=h)
    assert r.status_code==403

def test_campus_admin_cannot_open_accounts_refunds_module():
    h=_login("campus@gaintacademy.com")
    r=client.get("/api/v1/module-access/Refunds",headers=h)
    assert r.status_code==403

def test_teacher_cannot_open_audit_trail_module():
    h=_login("teacher@gaintacademy.com")
    r=client.get("/api/v1/module-access/Audit%20Trail",headers=h)
    assert r.status_code==403

def test_parent_cannot_open_staff_module():
    h=_login("parent@gaintacademy.com")
    r=client.get("/api/v1/module-access/Staff",headers=h)
    assert r.status_code==403


def test_non_admin_cannot_modify_users():
    student=_login("student@gaintacademy.com")
    me=client.get("/api/v1/auth/me",headers=student).json()
    r=client.patch(f"/api/v1/users/{me['id']}",headers=student,json={"name":"Changed"})
    assert r.status_code==403

def test_admin_cannot_remove_own_admin_role_or_deactivate_self():
    admin=_login("admin@gaintacademy.com")
    me=client.get("/api/v1/auth/me",headers=admin).json()
    assert client.patch(f"/api/v1/users/{me['id']}",headers=admin,json={"role":"Teacher"}).status_code==409
    assert client.patch(f"/api/v1/users/{me['id']}",headers=admin,json={"is_active":False}).status_code==409

def test_admin_rejects_unsupported_role():
    admin=_login("admin@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    target=next(x for x in users if x["role"]=="Student")
    r=client.patch(f"/api/v1/users/{target['id']}",headers=admin,json={"role":"Super Admin"})
    assert r.status_code==400


def test_admin_can_create_tenant_locked_user():
    admin=_login("admin@gaintacademy.com")
    r=client.post("/api/v1/users",headers=admin,json={"name":"New Teacher","email":"new.teacher@test.local","password":"Teacher@123","role":"Teacher","campus_id":1})
    assert r.status_code==200
    assert r.json()["role"]=="Teacher"

def test_user_creation_rejects_duplicate_email_and_weak_password():
    admin=_login("admin@gaintacademy.com")
    duplicate=client.post("/api/v1/users",headers=admin,json={"name":"Duplicate","email":"student@gaintacademy.com","password":"Strong@123","role":"Student","campus_id":1})
    assert duplicate.status_code==409
    weak=client.post("/api/v1/users",headers=admin,json={"name":"Weak User","email":"weak@test.local","password":"password","role":"Student","campus_id":1})
    assert weak.status_code==400

def test_non_admin_cannot_create_user():
    teacher=_login("teacher@gaintacademy.com")
    r=client.post("/api/v1/users",headers=teacher,json={"name":"Blocked User","email":"blocked@test.local","password":"Blocked@123","role":"Student","campus_id":1})
    assert r.status_code==403


def test_admin_parent_student_link_management():
    admin=_login("admin@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    parent=next(x for x in users if x["role"]=="Parent / Guardian")
    student=next(x for x in users if x["role"]=="Student")
    existing=client.get("/api/v1/admin/parent-student-links",headers=admin)
    assert existing.status_code==200
    if not any(x["parent_user_id"]==parent["id"] and x["student_user_id"]==student["id"] for x in existing.json()):
        made=client.post("/api/v1/admin/parent-student-links",headers=admin,json={"parent_user_id":parent["id"],"student_user_id":student["id"],"relationship":"Guardian"})
        assert made.status_code==200

def test_non_admin_cannot_manage_parent_student_links():
    teacher=_login("teacher@gaintacademy.com")
    assert client.get("/api/v1/admin/parent-student-links",headers=teacher).status_code==403


def test_admissions_lifecycle_and_history():
    admin=_login("admin@gaintacademy.com")
    units=client.get("/api/v1/academic-structure",headers=admin).json()
    def ensure_unit(unit_type,name,code,parent_id=None):
        existing=next((x for x in units if x["unit_type"]==unit_type),None)
        if existing: return existing
        made=client.post("/api/v1/academic-structure",headers=admin,json={"unit_type":unit_type,"name":name,"code":code,"parent_id":parent_id,"campus_id":1,"status":"Active"})
        assert made.status_code==200, made.text
        row=made.json(); units.append(row); return row
    campus=ensure_unit("CAMPUS","CI Campus","CI-CAMP")
    faculty=ensure_unit("SCHOOL_FACULTY","CI Faculty","CI-FAC",campus["id"])
    department=ensure_unit("DEPARTMENT","CI Department","CI-DEPT",faculty["id"])
    program=ensure_unit("PROGRAM","CI Test Program","CI-PROG",department["id"])
    period=ensure_unit("ACADEMIC_PERIOD","CI Academic Period","CI-PER",program["id"])
    course=ensure_unit("COURSE","CI Test Course","CI-COURSE",period["id"])
    sections=[x for x in units if x["unit_type"]=="SECTION_BATCH"]
    if not sections:
        sections=[ensure_unit("SECTION_BATCH","CI Test Section","CI-SEC",course["id"])]
    email="admission.lifecycle@test.local"
    users=client.get("/api/v1/users",headers=admin).json()
    existing=next((x for x in users if x["email"]==email),None)
    if existing:
        student_id=existing["id"]
    else:
        r=client.post("/api/v1/admissions/enroll-student",headers=admin,json={
            "name":"Admission Lifecycle","email":email,"password":"Student@123",
            "campus_id":1,"program_unit_id":program["id"],"section_unit_id":sections[0]["id"],
            "course_unit_ids":[],"parent_user_id":None,"relationship":"Guardian"
        })
        assert r.status_code==200, r.text
        student_id=r.json()["id"]
    profile=client.get(f"/api/v1/admissions/students/{student_id}/profile",headers=admin)
    assert profile.status_code==200
    assert profile.json()["status"]=="Active"
    if len(sections)>1:
        moved=client.patch(f"/api/v1/admissions/students/{student_id}",headers=admin,json={"section_unit_id":sections[1]["id"]})
        assert moved.status_code==200
    withdrawn=client.patch(f"/api/v1/admissions/students/{student_id}",headers=admin,json={"status":"Withdrawn"})
    assert withdrawn.status_code==200
    reactivated=client.patch(f"/api/v1/admissions/students/{student_id}",headers=admin,json={"status":"Active"})
    assert reactivated.status_code==200
    history=client.get(f"/api/v1/admissions/students/{student_id}/history",headers=admin)
    assert history.status_code==200
    events={x["event_type"] for x in history.json()}
    assert "ENROLLED" in events
    assert "WITHDRAWN" in events
    assert "REACTIVATED" in events

def test_admissions_endpoints_reject_non_admin_roles():
    teacher=_login("teacher@gaintacademy.com")
    assert client.get("/api/v1/admissions/students",headers=teacher).status_code==403
    assert client.get("/api/v1/admissions/summary",headers=teacher).status_code==403
    assert client.post("/api/v1/admissions/enroll-student",headers=teacher,json={
        "name":"Blocked Student","email":"blocked.admission@test.local","password":"Student@123",
        "campus_id":1,"program_unit_id":1,"course_unit_ids":[]
    }).status_code==403

def test_admissions_guardian_link_is_reflected_in_student_list():
    admin=_login("admin@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    parent=next(x for x in users if x["role"]=="Parent / Guardian")
    student=next(x for x in users if x["role"]=="Student")
    links=client.get("/api/v1/admin/parent-student-links",headers=admin).json()
    if not any(x["parent_user_id"]==parent["id"] and x["student_user_id"]==student["id"] for x in links):
        r=client.post("/api/v1/admin/parent-student-links",headers=admin,json={
            "parent_user_id":parent["id"],"student_user_id":student["id"],"relationship":"Guardian"
        })
        assert r.status_code==200
    rows=client.get("/api/v1/admissions/students",headers=admin)
    assert rows.status_code==200
    target=next(x for x in rows.json() if x["id"]==student["id"])
    assert target["has_guardian"] is True


def test_student_management_actions_and_rbac():
    admin=_login("admin@gaintacademy.com")
    teacher=_login("teacher@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    student=next(x for x in users if x["role"]=="Student")
    parent=next(x for x in users if x["role"]=="Parent / Guardian")
    assert client.patch(f"/api/v1/admin/students/{student['id']}",headers=teacher,json={"name":"Blocked"}).status_code==403
    assert client.put(f"/api/v1/admin/students/{student['id']}/guardian",headers=teacher,json={"parent_user_id":parent["id"],"relationship":"Guardian"}).status_code==403
    changed=client.patch(f"/api/v1/admin/students/{student['id']}",headers=admin,json={"name":student["name"]})
    assert changed.status_code==200, changed.text
    linked=client.put(f"/api/v1/admin/students/{student['id']}/guardian",headers=admin,json={"parent_user_id":parent["id"],"relationship":"Guardian"})
    assert linked.status_code==200, linked.text
    profile=client.get(f"/api/v1/admissions/students/{student['id']}/profile",headers=admin)
    assert profile.status_code==200
    assert any(g["id"]==parent["id"] for g in profile.json()["guardians"])
    removed=client.delete(f"/api/v1/admin/students/{student['id']}/guardian",headers=admin)
    assert removed.status_code==200
    profile=client.get(f"/api/v1/admissions/students/{student['id']}/profile",headers=admin).json()
    assert profile["guardians"]==[]

def test_student_academic_management_validates_unit_type():
    admin=_login("admin@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    student=next(x for x in users if x["role"]=="Student")
    units=client.get("/api/v1/academic-structure",headers=admin).json()
    non_section=next((x for x in units if x["unit_type"]!="SECTION_BATCH"),None)
    if non_section:
        r=client.put(f"/api/v1/admin/students/{student['id']}/academics",headers=admin,json={"section_unit_id":non_section["id"]})
        assert r.status_code==400


def test_teacher_assignment_management_rbac_and_validation():
    admin=_login("admin@gaintacademy.com")
    student_headers=_login("student@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    teacher=next(x for x in users if x["role"]=="Teacher")
    units=client.get("/api/v1/academic-structure",headers=admin).json()
    course=next((x for x in units if x["unit_type"]=="COURSE"),None)
    section=next((x for x in units if x["unit_type"]=="SECTION_BATCH"),None)
    program=next((x for x in units if x["unit_type"]=="PROGRAM"),None)
    if course:
        blocked=client.post("/api/v1/academic-assignments",headers=student_headers,json={"user_id":teacher["id"],"unit_id":course["id"],"assignment_type":"FACULTY_ASSIGNMENT","status":"Active"})
        assert blocked.status_code==403
        made=client.post("/api/v1/academic-assignments",headers=admin,json={"user_id":teacher["id"],"unit_id":course["id"],"assignment_type":"FACULTY_ASSIGNMENT","status":"Active"})
        assert made.status_code in (200,409), made.text
    if section:
        made=client.post("/api/v1/academic-assignments",headers=admin,json={"user_id":teacher["id"],"unit_id":section["id"],"assignment_type":"FACULTY_ASSIGNMENT","status":"Active"})
        assert made.status_code in (200,409), made.text
    if program:
        advisor=client.post("/api/v1/academic-assignments",headers=admin,json={"user_id":teacher["id"],"unit_id":program["id"],"assignment_type":"ADVISOR_ASSIGNMENT","status":"Active"})
        assert advisor.status_code in (200,409), advisor.text
    student=next(x for x in users if x["role"]=="Student")
    if course:
        invalid=client.post("/api/v1/academic-assignments",headers=admin,json={"user_id":student["id"],"unit_id":course["id"],"assignment_type":"FACULTY_ASSIGNMENT","status":"Active"})
        assert invalid.status_code==400


def test_student_profile_is_self_scoped_and_student_only():
    student_headers=_login("student@gaintacademy.com")
    teacher_headers=_login("teacher@gaintacademy.com")
    profile=client.get("/api/v1/student/profile",headers=student_headers)
    assert profile.status_code==200, profile.text
    data=profile.json()
    assert data["email"]=="student@gaintacademy.com"
    assert data["status"] in ("Active","Withdrawn")
    assert isinstance(data["academics"],list)
    assert isinstance(data["guardians"],list)
    assert client.get("/api/v1/student/profile",headers=teacher_headers).status_code==403


def test_student_transport_is_self_scoped_and_student_only():
    student_headers=_login("student@gaintacademy.com")
    teacher_headers=_login("teacher@gaintacademy.com")
    response=client.get("/api/v1/student/transport",headers=student_headers)
    assert response.status_code==200, response.text
    data=response.json()
    assert "allocated" in data
    assert client.get("/api/v1/student/transport",headers=teacher_headers).status_code==403


def test_student_library_is_self_scoped_and_student_only():
    student_headers=_login("student@gaintacademy.com")
    teacher_headers=_login("teacher@gaintacademy.com")
    response=client.get("/api/v1/student/library",headers=student_headers)
    assert response.status_code==200, response.text
    assert isinstance(response.json(),list)
    assert client.get("/api/v1/student/library",headers=teacher_headers).status_code==403


def test_student_events_are_student_scoped_and_role_protected():
    student_headers=_login("student@gaintacademy.com")
    teacher_headers=_login("teacher@gaintacademy.com")
    response=client.get("/api/v1/student/events",headers=student_headers)
    assert response.status_code==200, response.text
    assert isinstance(response.json(),list)
    assert client.get("/api/v1/student/events",headers=teacher_headers).status_code==403


def test_student_grievance_create_list_and_rbac():
    student_headers=_login("student@gaintacademy.com")
    teacher_headers=_login("teacher@gaintacademy.com")
    created=client.post("/api/v1/student/grievances",headers=student_headers,json={
        "category":"Academic","subject":"Test support request","details":"Need assistance with an academic issue.","priority":"Normal"
    })
    assert created.status_code==200, created.text
    ticket=created.json()["ticket_no"]
    assert ticket.startswith("GR-")
    rows=client.get("/api/v1/student/grievances",headers=student_headers)
    assert rows.status_code==200
    assert any(x["ticket_no"]==ticket for x in rows.json())
    assert client.get("/api/v1/student/grievances",headers=teacher_headers).status_code==403
    assert client.post("/api/v1/student/grievances",headers=student_headers,json={
        "category":"Academic","subject":"","details":"","priority":"Normal"
    }).status_code==400


def test_teacher_self_service_modules_are_role_protected():
    teacher=_login("teacher@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    for path in ("/api/v1/teacher/notes","/api/v1/teacher/communication","/api/v1/teacher/communication/recipients","/api/v1/teacher/events","/api/v1/teacher/leave"):
        response=client.get(path,headers=teacher)
        assert response.status_code==200, response.text
        assert client.get(path,headers=student).status_code==403


def test_teacher_leave_validation_and_self_service():
    teacher=_login("teacher@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    created=client.post("/api/v1/teacher/leave",headers=teacher,json={
        "leave_type":"Casual","start_date":"2026-10-10","end_date":"2026-10-11","reason":"Personal work"
    })
    assert created.status_code==200, created.text
    leave_id=created.json()["id"]
    rows=client.get("/api/v1/teacher/leave",headers=teacher)
    assert rows.status_code==200
    assert any(x["id"]==leave_id for x in rows.json())
    assert client.post("/api/v1/teacher/leave",headers=teacher,json={
        "leave_type":"Casual","start_date":"2026-10-12","end_date":"2026-10-11","reason":"Invalid dates"
    }).status_code==400
    assert client.post("/api/v1/teacher/leave",headers=student,json={
        "leave_type":"Casual","start_date":"2026-10-10","end_date":"2026-10-11","reason":"Blocked"
    }).status_code==403


def test_teacher_notes_and_communication_reject_unassigned_student():
    teacher=_login("teacher@gaintacademy.com")
    admin=_login("admin@gaintacademy.com")
    users=client.get("/api/v1/users",headers=admin).json()
    student=next(x for x in users if x["role"]=="Student")
    roster=client.get("/api/v1/teacher-roster",headers=teacher)
    assert roster.status_code==200
    assigned={x["student_user_id"] for x in roster.json().get("students",[])}
    if student["id"] not in assigned:
        note=client.post("/api/v1/teacher/notes",headers=teacher,json={
            "student_user_id":student["id"],"subject":"Blocked note","note":"Must not be accepted","visibility":"PRIVATE"
        })
        assert note.status_code==403
        message=client.post("/api/v1/teacher/communication",headers=teacher,json={
            "recipient_user_id":student["id"],"student_user_id":student["id"],"subject":"Blocked message","body":"Must not be accepted"
        })
        assert message.status_code==403


def test_teacher_core_academic_endpoints_are_role_protected():
    teacher=_login("teacher@gaintacademy.com")
    parent=_login("parent@gaintacademy.com")
    for path in ("/api/v1/teacher-roster","/api/v1/class-sessions"):
        response=client.get(path,headers=teacher)
        assert response.status_code==200, response.text
        assert client.get(path,headers=parent).status_code==403


def test_teacher_event_endpoint_is_teacher_only():
    teacher=_login("teacher@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    response=client.get("/api/v1/teacher/events",headers=teacher)
    assert response.status_code==200, response.text
    assert isinstance(response.json(),list)
    assert client.get("/api/v1/teacher/events",headers=student).status_code==403


def test_campus_admin_rejects_invalid_operational_data():
    h=_login("campus@gaintacademy.com")
    assert client.post("/api/v1/campus/inventory",headers=h,json={
        "name":"Invalid Stock","category":"Test","item_code":"NEG-STOCK","quantity":-1,
        "minimum_quantity":0,"location":"Store","status":"ACTIVE","notes":""
    }).status_code in (400,422)
    assert client.post("/api/v1/campus/assets",headers=h,json={
        "asset_code":"","name":"","category":"IT","serial_number":"","location":"",
        "assigned_to":"","condition":"GOOD","status":"ACTIVE","notes":""
    }).status_code in (400,422)
    assert client.post("/api/v1/campus/events",headers=h,json={
        "title":"","event_type":"General","venue":"Hall","starts_at":"2026-10-10T10:00:00",
        "ends_at":"2026-10-10T11:00:00","audience_role":"ALL","registration_required":False
    }).status_code in (400,422)


def test_campus_admin_mutations_are_role_protected():
    student=_login("student@gaintacademy.com")
    assert client.post("/api/v1/campus/visitors",headers=student,json={
        "name":"Blocked","phone":"","purpose":"Test","person_to_meet":""
    }).status_code==403
    assert client.post("/api/v1/campus/inventory",headers=student,json={
        "name":"Blocked","category":"Test","item_code":"BLOCK","quantity":1,
        "minimum_quantity":0,"location":"","status":"ACTIVE","notes":""
    }).status_code==403


def test_auditor_workspace_is_read_only_and_role_protected():
    auditor=_login("auditor@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    for path in ("/api/v1/auditor/dashboard","/api/v1/auditor/compliance","/api/v1/auditor/exceptions","/api/v1/auditor/evidence","/api/v1/auditor/export-reports"):
        assert client.get(path,headers=auditor).status_code==200
        assert client.get(path,headers=student).status_code==403
    assert client.get("/api/v1/audit",headers=auditor).status_code==200
    assert client.post("/api/v1/hr/recruitment",headers=auditor,json={
        "name":"Blocked Auditor Mutation","email":"auditor-blocked@example.com","position":"Teacher"
    }).status_code==403
    assert client.post("/api/v1/campus/inventory",headers=auditor,json={
        "name":"Blocked","category":"Audit","item_code":"AUD-BLOCK","quantity":1,
        "minimum_quantity":0,"location":"Store","status":"ACTIVE","notes":""
    }).status_code==403


def test_auditor_evidence_summary_matches_returned_tenant_records():
    auditor=_login("auditor@gaintacademy.com")
    response=client.get("/api/v1/auditor/evidence",headers=auditor)
    assert response.status_code==200
    data=response.json()
    rows=data["evidence"]
    assert data["summary"]["total"]>=len(rows)
    assert all(x["status"] in {"AVAILABLE","MISSING"} for x in rows)
    assert all(x["module"] in {"HR","Finance","Admissions","Audit"} for x in rows)


def test_parent_role_endpoints_are_protected():
    parent=_login("parent@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    paths=[
        "/api/v1/parents/dashboard",
        "/api/v1/parents/children",
        "/api/v1/parents/messages",
        "/api/v1/parents/messages/recipients",
        "/api/v1/parents/events",
        "/api/v1/parents/grievances",
        "/api/v1/parents/leave",
    ]
    for path in paths:
        assert client.get(path,headers=parent).status_code==200
        assert client.get(path,headers=student).status_code==403


def test_parent_leave_rejects_unlinked_student_and_invalid_dates():
    parent=_login("parent@gaintacademy.com")
    children=client.get("/api/v1/parents/children",headers=parent).json()
    if children:
        child_id=children[0]["id"]
        bad=client.post("/api/v1/parents/leave",headers=parent,json={
            "student_user_id":child_id,"leave_type":"Sick",
            "start_date":"2026-10-10","end_date":"2026-10-09","reason":"Medical rest"})
        assert bad.status_code==400
    response=client.post("/api/v1/parents/leave",headers=parent,json={
        "student_user_id":999999,"leave_type":"Casual",
        "start_date":"2026-10-10","end_date":"2026-10-11","reason":"Family reason"})
    assert response.status_code==403


def test_parent_child_detail_endpoints_reject_unlinked_student():
    parent=_login("parent@gaintacademy.com")
    for suffix in ("fees","academics","transport","location"):
        response=client.get(f"/api/v1/parents/children/999999/{suffix}",headers=parent)
        assert response.status_code==403, f"{suffix}: {response.text}"


def test_parent_message_rejects_invalid_teacher_context():
    parent=_login("parent@gaintacademy.com")
    children=client.get("/api/v1/parents/children",headers=parent).json()
    if not children:
        return
    response=client.post("/api/v1/parents/messages",headers=parent,json={
        "recipient_user_id":children[0]["id"],"student_user_id":children[0]["id"],
        "subject":"Test message","body":"Parent communication authorization test"})
    assert response.status_code==404


def test_hr_domain_endpoints_are_role_protected_and_auditor_read_only():
    hr=_login("hr@gaintacademy.com")
    auditor=_login("auditor@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    read_paths=[
        "/api/v1/hr/staff","/api/v1/hr/attendance","/api/v1/hr/leave",
        "/api/v1/hr/documents","/api/v1/hr/recruitment",
        "/api/v1/hr/performance","/api/v1/hr/reports",
    ]
    for path in read_paths:
        assert client.get(path,headers=hr).status_code==200
        assert client.get(path,headers=auditor).status_code==200
        assert client.get(path,headers=student).status_code==403

    staff=client.get("/api/v1/hr/staff",headers=hr).json()
    teacher=next(x for x in staff if x["role"]=="Teacher")
    assert client.post("/api/v1/hr/attendance",headers=auditor,json={
        "staff_user_id":teacher["id"],"attendance_date":"2026-09-29","status":"PRESENT","note":""
    }).status_code==403
    assert client.post("/api/v1/hr/documents",headers=auditor,json={
        "staff_user_id":teacher["id"],"document_type":"ID Proof","title":"Audit attempt"
    }).status_code==403
    assert client.post("/api/v1/hr/recruitment",headers=auditor,json={
        "name":"Audit Candidate","email":"audit-candidate@example.com","position":"Teacher"
    }).status_code==403
    assert client.post("/api/v1/hr/performance",headers=auditor,json={
        "staff_user_id":teacher["id"],"review_period":"Q3 2026","rating":4
    }).status_code==403


def test_hr_attendance_and_performance_validate_staff_scope():
    hr=_login("hr@gaintacademy.com")
    assert client.post("/api/v1/hr/attendance",headers=hr,json={
        "staff_user_id":999999,"attendance_date":"2026-09-29","status":"PRESENT","note":""
    }).status_code==400
    assert client.post("/api/v1/hr/performance",headers=hr,json={
        "staff_user_id":999999,"review_period":"Q3 2026","rating":4
    }).status_code==400
    staff=client.get("/api/v1/hr/staff",headers=hr).json()
    teacher=next(x for x in staff if x["role"]=="Teacher")
    assert client.post("/api/v1/hr/attendance",headers=hr,json={
        "staff_user_id":teacher["id"],"attendance_date":"2026-09-29","status":"INVALID","note":""
    }).status_code==400
    assert client.post("/api/v1/hr/performance",headers=hr,json={
        "staff_user_id":teacher["id"],"review_period":"Q3 2026","rating":6
    }).status_code==422


def test_hr_rejects_inactive_staff_and_duplicate_active_candidate():
    hr=_login("hr@gaintacademy.com")
    staff=client.get("/api/v1/hr/staff",headers=hr).json()
    teacher=next(x for x in staff if x["role"]=="Teacher")
    with SessionLocal() as db:
        target=db.get(User,teacher["id"])
        target.is_active=False
        db.commit()
    assert client.post("/api/v1/hr/attendance",headers=hr,json={
        "staff_user_id":teacher["id"],"attendance_date":"2026-09-30","status":"PRESENT","note":""
    }).status_code==400
    assert client.post("/api/v1/hr/documents",headers=hr,json={
        "staff_user_id":teacher["id"],"document_type":"ID Proof","title":"Identity"
    }).status_code==400
    assert client.post("/api/v1/hr/performance",headers=hr,json={
        "staff_user_id":teacher["id"],"review_period":"Q3 2026","rating":4
    }).status_code==400
    candidate={"name":"Test Candidate","email":"candidate-unique@example.com","position":"Teacher"}
    assert client.post("/api/v1/hr/recruitment",headers=hr,json=candidate).status_code==200
    assert client.post("/api/v1/hr/recruitment",headers=hr,json=candidate).status_code==409


def test_hr_mutations_reject_non_hr_roles():
    student=_login("student@gaintacademy.com")
    assert client.post("/api/v1/hr/recruitment",headers=student,json={
        "name":"Blocked","email":"blocked@example.com","position":"Teacher"
    }).status_code==403
    assert client.patch("/api/v1/hr/leave/999999",headers=student,json={
        "status":"APPROVED","reviewer_note":""
    }).status_code==403


def test_campus_admin_endpoints_are_role_protected():
    campus=_login("campus@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    read_paths=[
        "/api/v1/campus/dashboard","/api/v1/campus/students","/api/v1/campus/staff",
        "/api/v1/campus/attendance","/api/v1/campus/transport","/api/v1/campus/live-locations",
        "/api/v1/campus/visitors","/api/v1/campus/inventory","/api/v1/campus/assets",
        "/api/v1/campus/events","/api/v1/campus/grievances","/api/v1/campus/reports",
    ]
    for path in read_paths:
        response=client.get(path,headers=campus)
        assert response.status_code==200, f"{path}: {response.text}"
        assert client.get(path,headers=student).status_code==403


def test_campus_admin_write_endpoints_reject_other_roles_and_invalid_values():
    campus=_login("campus@gaintacademy.com")
    student=_login("student@gaintacademy.com")
    visitor={"name":"Campus Visitor","phone":"9999999999","purpose":"Meeting","person_to_meet":"Office"}
    assert client.post("/api/v1/campus/visitors",headers=student,json=visitor).status_code==403
    assert client.post("/api/v1/campus/inventory",headers=campus,json={
        "name":"Invalid Stock","category":"General","quantity":1,"minimum_quantity":0,"status":"BROKEN"
    }).status_code==400
    assert client.post("/api/v1/campus/assets",headers=campus,json={
        "asset_code":"TEST-BAD-CONDITION","name":"Test Asset","condition":"UNKNOWN","status":"ACTIVE"
    }).status_code==400
    assert client.post("/api/v1/campus/events",headers=campus,json={
        "title":"Invalid Event","starts_at":"2026-10-10T12:00:00","ends_at":"2026-10-10T11:00:00",
        "audience_role":"ALL"
    }).status_code==400


def test_campus_student_listing_is_campus_isolated():
    admin=_login("admin@gaintacademy.com")
    campus=_login("campus@gaintacademy.com")
    created=client.post("/api/v1/users",headers=admin,json={
        "name":"Other Campus Student","email":"campus.isolation@test.local",
        "password":"Campus@123","role":"Student","campus_id":2
    })
    assert created.status_code in (200,409), created.text
    rows=client.get("/api/v1/campus/students",headers=campus)
    assert rows.status_code==200
    assert all(x["campus_id"]==1 for x in rows.json())
    assert not any(x["email"]=="campus.isolation@test.local" for x in rows.json())


def test_adaptive_institution_admin_demo_accounts_resolve_correct_types():
    cases = [
        ("admin@gaintacademy.com", "UNIVERSITY", "GAINT Demo University"),
        ("school.admin@gaintacademy.com", "SCHOOL", "GAINT Demo School"),
        ("college.admin@gaintacademy.com", "COLLEGE", "GAINT Demo College"),
    ]
    for email, expected_type, expected_name in cases:
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "Password@123"})
        assert response.status_code == 200
        user = response.json()["user"]
        assert user["role"] == "Institution Admin"
        assert user["institution"]["institution_type"] == expected_type
        assert user["institution"]["name"] == expected_name


def test_school_and_college_full_role_matrix_login_and_tenant_isolation():
    role_accounts = [
        ("admin", "Institution Admin"),
        ("teacher", "Teacher"),
        ("student", "Student"),
        ("parent", "Parent / Guardian"),
        ("accounts", "Accounts"),
        ("hr", "HR"),
        ("campus", "Campus Admin"),
        ("auditor", "Auditor"),
    ]
    for prefix, tenant_id, institution_type in [
        ("school", 2, "SCHOOL"),
        ("college", 3, "COLLEGE"),
    ]:
        for account, expected_role in role_accounts:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": f"{prefix}.{account}@gaintacademy.com", "password": "Password@123"},
            )
            assert response.status_code == 200
            user = response.json()["user"]
            assert user["role"] == expected_role
            assert user["tenant_id"] == tenant_id
            assert user["institution"]["institution_type"] == institution_type
