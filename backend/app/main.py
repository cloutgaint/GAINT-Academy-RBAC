from typing import Optional
import datetime as dt
from decimal import Decimal
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session

from .config import settings
from .database import Base, engine, SessionLocal, get_db
from .models import User, Institution, AcademicUnit, AcademicAssignment, EnrollmentHistory, AcademicWork, StudentAcademicWork, ClassSession, AttendanceEntry, GradeRule, ExamResult, FeeLedger, FeePayment, FeeConcession, FeeRefund, FinanceReconciliation, Record, ParentStudentLink, StudentLocation, SosEvent, Audit, TransportRoute, TransportVehicle, TransportStop, StudentTransportAllocation, LibraryBook, LibraryLoan, AcademyEvent, EventRegistration, Grievance, TeacherNote, CommunicationMessage, TeacherLeaveRequest, StudentLeaveRequest, StaffAttendance, StaffDocument, RecruitmentCandidate, StaffPerformanceReview, CampusVisitor, CampusInventoryItem, CampusAsset, Hostel, HostelRoom, HostelAllocation, HealthRecord, HealthVisit
from .schemas import LoginRequest, RecordIn, LocationUpdate, SosIn, AIChatRequest, InstitutionIn, AcademicUnitIn, AcademicAssignmentIn, AcademicActivityIn, AcademicWorkIn, AcademicWorkUpdateIn, SubmissionIn, GradeIn, ClassSessionIn, ClassSessionUpdateIn, AttendanceMarkIn, GradeRuleIn, ExamResultIn, FeeLedgerIn, FeeLedgerUpdateIn, FeePaymentIn, FeeConcessionIn, FeeRefundIn, FinanceReconciliationIn, UserAdminUpdate, UserAdminCreate, ParentStudentLinkIn, StudentEnrollmentIn, StudentEnrollmentUpdate, StudentAdminUpdate, StudentAcademicManagementIn, StudentGuardianManagementIn, GrievanceIn, TeacherNoteIn, TeacherNoteUpdateIn, TeacherMessageIn, TeacherLeaveIn, ParentStudentLeaveIn, StaffAttendanceIn, HRLeaveReviewIn, StaffDocumentIn, RecruitmentCandidateIn, RecruitmentStageIn, StaffPerformanceReviewIn, CampusVisitorIn, CampusVisitorStatusIn, CampusInventoryIn, CampusInventoryUpdate, CampusAssetIn, CampusAssetUpdate, CampusEventIn, CampusGrievanceUpdateIn, HostelIn, HostelRoomIn, HostelUpdateIn, HostelRoomUpdateIn, HostelAllocationIn, HostelCheckoutIn, HealthRecordIn, HealthVisitIn, AdminLibraryBookIn, AdminLibraryBookUpdate, AdminLibraryLoanIn, AdminLibraryReturnIn, AdminTransportRouteIn, AdminTransportVehicleIn, AdminTransportStopIn, AdminTransportAllocationIn, AdminTransportStatusUpdate, AdminTransportRouteUpdate, AdminTransportVehicleUpdate, AdminClassSessionIn, AdminClassSessionUpdate, AdminInventoryIn, AdminAssetIn, AdminAcademicWorkIn, AdminAcademicWorkUpdate, AdminEventUpdateIn
from .security import verify_password, hash_password, create_token, current_user, require_roles
from .rbac import ROLE_MENUS, dashboard_for, module_access_for, can
from .seed import seed, DEMO_PASSWORD, DEMO_USERS

settings.validate_runtime()
if settings.AUTO_CREATE_SCHEMA:
    Base.metadata.create_all(bind=engine)
if settings.SEED_DEMO_DATA:
    with SessionLocal() as db:
        seed(db)

app = FastAPI(
    title="GAINT Academy API",
    version="2.0.0",
    description="GAINT Academy role-based education, campus and safety platform",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in settings.CORS_ORIGINS.split(",") if x.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def audit(db: Session, user: User, action: str, resource: str, details: str = ""):
    db.add(Audit(
        tenant_id=user.tenant_id,
        actor=user.email,
        action=action,
        resource=resource,
        details=details,
    ))

@app.get("/")
def root():
    return {
        "service":"GAINT Academy API",
        "version":"2.0.0",
        "status":"running",
        "docs":"/docs",
        "health":"/health",
    }

@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(select(1))
    except Exception:
        raise HTTPException(503, "Database unavailable")
    return {"status":"ok","service":"GAINT Academy API","database":"ok"}

@app.get("/api/v1/demo-accounts")
def demo_accounts():
    if not settings.SEED_DEMO_DATA:
        raise HTTPException(404, "Demo accounts are disabled")
    return {
        "password": DEMO_PASSWORD,
        "accounts":[{"email":e,"name":n,"role":r} for e,n,r in DEMO_USERS],
    }

def institution_payload(db: Session, tenant_id: int):
    row = db.get(Institution, tenant_id)
    if not row:
        return {"id": tenant_id, "name": "GAINT Academy", "institution_type": "UNIVERSITY", "code": ""}
    return {"id": row.id, "name": row.name, "institution_type": row.institution_type, "code": row.code}

@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(User.email==email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {
        "access_token":create_token(user),
        "token_type":"bearer",
        "user":{
            "id":user.id,"name":user.name,"email":user.email,"role":user.role,
            "tenant_id":user.tenant_id,"campus_id":user.campus_id,
            "institution": institution_payload(db, user.tenant_id),
        }
    }

@app.get("/api/v1/auth/me")
def me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return {
        "id":user.id,"name":user.name,"email":user.email,"role":user.role,
        "tenant_id":user.tenant_id,"campus_id":user.campus_id,
        "institution": institution_payload(db, user.tenant_id),
    }

@app.get("/api/v1/institution")
def institution_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return institution_payload(db, user.tenant_id)

@app.put("/api/v1/institution")
def update_institution(payload: InstitutionIn, user: User = Depends(require_roles("Institution Admin")), db: Session = Depends(get_db)):
    institution_type = payload.institution_type.strip().upper()
    if institution_type not in {"SCHOOL","COLLEGE","UNIVERSITY","TRAINING_INSTITUTE"}:
        raise HTTPException(400, "Unsupported institution type")
    row = db.get(Institution, user.tenant_id)
    if not row:
        row = Institution(id=user.tenant_id, name=payload.name.strip(), institution_type=institution_type, code=payload.code.strip().upper())
        db.add(row)
    else:
        row.name = payload.name.strip()
        row.institution_type = institution_type
        row.code = payload.code.strip().upper()
    audit(db, user, "UPDATE", "institution", institution_type)
    db.commit(); db.refresh(row)
    return institution_payload(db, user.tenant_id)

@app.get("/api/v1/academic-structure")
def academic_structure(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id == user.tenant_id).order_by(AcademicUnit.unit_type, AcademicUnit.name)).all()
    return [{"id":r.id,"unit_type":r.unit_type,"name":r.name,"code":r.code,"parent_id":r.parent_id,"campus_id":r.campus_id,"status":r.status} for r in rows]

@app.post("/api/v1/academic-structure")
def create_academic_unit(payload: AcademicUnitIn, user: User = Depends(require_roles("Institution Admin")), db: Session = Depends(get_db)):
    allowed={"CAMPUS","SCHOOL_FACULTY","DEPARTMENT","PROGRAM","ACADEMIC_PERIOD","COURSE","SECTION_BATCH"}
    unit_type=payload.unit_type.strip().upper()
    if unit_type not in allowed:
        raise HTTPException(400,"Unsupported academic unit type")
    hierarchy={
        "CAMPUS":set(),
        "SCHOOL_FACULTY":{"CAMPUS"},
        "DEPARTMENT":{"SCHOOL_FACULTY"},
        "PROGRAM":{"DEPARTMENT"},
        "ACADEMIC_PERIOD":{"PROGRAM"},
        "COURSE":{"ACADEMIC_PERIOD"},
        "SECTION_BATCH":{"COURSE"},
    }
    parent=None
    if payload.parent_id is not None:
        parent=db.get(AcademicUnit,payload.parent_id)
        if not parent or parent.tenant_id != user.tenant_id:
            raise HTTPException(400,"Invalid parent academic unit")
    expected=hierarchy[unit_type]
    if not expected and parent is not None:
        raise HTTPException(400,f"{unit_type} must be a top-level academic unit")
    if expected and parent is None:
        raise HTTPException(400,f"{unit_type} requires a parent academic unit")
    if parent is not None and parent.unit_type not in expected:
        allowed=", ".join(sorted(expected))
        raise HTTPException(400,f"{unit_type} must be created under: {allowed}")
    code=payload.code.strip().upper()
    duplicate=db.scalar(select(AcademicUnit).where(
        AcademicUnit.tenant_id==user.tenant_id,
        AcademicUnit.code==code,
    ))
    if duplicate: raise HTTPException(409,"Academic unit code already exists in this institution")
    row=AcademicUnit(tenant_id=user.tenant_id,campus_id=payload.campus_id,unit_type=unit_type,name=payload.name.strip(),code=code,parent_id=payload.parent_id,status=payload.status)
    db.add(row); audit(db,user,"CREATE","academic_structure",f"{unit_type}:{row.name}"); db.commit(); db.refresh(row)
    return {"id":row.id,"unit_type":row.unit_type,"name":row.name,"code":row.code,"parent_id":row.parent_id,"campus_id":row.campus_id,"status":row.status}

@app.put("/api/v1/academic-structure/{unit_id}")
def update_academic_unit(unit_id:int,payload:AcademicUnitIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(AcademicUnit).where(AcademicUnit.id==unit_id,AcademicUnit.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Academic unit not found")
    if payload.unit_type.strip().upper()!=row.unit_type: raise HTTPException(400,"Academic unit type cannot be changed")
    code=payload.code.strip().upper()
    duplicate=db.scalar(select(AcademicUnit.id).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.code==code,AcademicUnit.id!=unit_id))
    if duplicate: raise HTTPException(409,"Academic unit code already exists in this institution")
    if payload.parent_id!=row.parent_id: raise HTTPException(400,"Use academic structure workflow to change hierarchy")
    if payload.campus_id!=row.campus_id: raise HTTPException(400,"Campus cannot be changed after unit creation")
    status=payload.status.strip().title()
    if status not in {"Active","Inactive"}: raise HTTPException(400,"Invalid academic unit status")
    row.name=payload.name.strip(); row.code=code; row.status=status
    audit(db,user,"UPDATE","academic_structure",f"{row.unit_type}:{row.id}:{row.name}:{status}"); db.commit(); db.refresh(row)
    return {"id":row.id,"unit_type":row.unit_type,"name":row.name,"code":row.code,"parent_id":row.parent_id,"campus_id":row.campus_id,"status":row.status}

@app.put("/api/v1/admin/students/{student_id}/academics")
def admin_manage_student_academics(student_id:int,payload:StudentAcademicManagementIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    if payload.section_unit_id is not None:
        section=db.get(AcademicUnit,payload.section_unit_id)
        if not section or section.tenant_id!=user.tenant_id or section.unit_type!="SECTION_BATCH": raise HTTPException(400,"Invalid section or batch")
        old=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==student.id,AcademicAssignment.assignment_type=="SECTION_ASSIGNMENT")).all()
        previous=old[0].unit_id if old else None
        for row in old: db.delete(row)
        db.add(AcademicAssignment(tenant_id=user.tenant_id,user_id=student.id,unit_id=section.id,assignment_type="SECTION_ASSIGNMENT",status="Active"))
        if previous!=section.id: db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="SECTION_TRANSFER",from_unit_id=previous,to_unit_id=section.id,details="source=students",actor_user_id=user.id))
    if payload.course_unit_ids is not None:
        courses=[]
        for unit_id in dict.fromkeys(payload.course_unit_ids):
            unit=db.get(AcademicUnit,unit_id)
            if not unit or unit.tenant_id!=user.tenant_id or unit.unit_type!="COURSE": raise HTTPException(400,"Invalid course")
            courses.append(unit)
        old=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==student.id,AcademicAssignment.assignment_type=="COURSE_REGISTRATION")).all()
        for row in old: db.delete(row)
        db.add_all([AcademicAssignment(tenant_id=user.tenant_id,user_id=student.id,unit_id=x.id,assignment_type="COURSE_REGISTRATION",status="Active") for x in courses])
        db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="COURSES_UPDATED",details="courses="+",".join(str(x.id) for x in courses),actor_user_id=user.id))
    audit(db,user,"UPDATE","student_academics",f"student={student.id}")
    db.commit()
    return {"ok":True}

@app.put("/api/v1/admin/students/{student_id}/guardian")
def admin_manage_student_guardian(student_id:int,payload:StudentGuardianManagementIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id); parent=db.get(User,payload.parent_user_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    if not parent or parent.tenant_id!=user.tenant_id or parent.role!="Parent / Guardian" or not parent.is_active: raise HTTPException(400,"Invalid parent or guardian")
    old=db.scalars(select(ParentStudentLink).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.student_user_id==student.id)).all()
    for row in old: db.delete(row)
    db.flush()
    db.add(ParentStudentLink(parent_user_id=parent.id,student_user_id=student.id,relationship=payload.relationship.strip(),tenant_id=user.tenant_id))
    db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="GUARDIAN_UPDATED",details=f"parent={parent.id};relationship={payload.relationship.strip()}",actor_user_id=user.id))
    audit(db,user,"UPDATE","student_guardian",f"student={student.id};parent={parent.id}")
    db.commit()
    return {"ok":True}

@app.delete("/api/v1/admin/students/{student_id}/guardian")
def admin_remove_student_guardian(student_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    rows=db.scalars(select(ParentStudentLink).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.student_user_id==student.id)).all()
    for row in rows: db.delete(row)
    db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="GUARDIAN_REMOVED",details="",actor_user_id=user.id))
    audit(db,user,"DELETE","student_guardian",f"student={student.id}")
    db.commit()
    return {"ok":True}

@app.patch("/api/v1/admin/students/{student_id}")
def admin_update_student(student_id:int,payload:StudentAdminUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    data=payload.model_dump(exclude_unset=True)
    if "email" in data:
        email=data["email"].strip().lower()
        duplicate=db.scalar(select(User).where(User.email==email,User.id!=student.id))
        if duplicate: raise HTTPException(409,"Email address is already registered")
        student.email=email
    if "name" in data: student.name=data["name"].strip()
    if "campus_id" in data: student.campus_id=data["campus_id"]
    if "is_active" in data and student.is_active!=data["is_active"]:
        previous="ACTIVE" if student.is_active else "WITHDRAWN"
        student.is_active=data["is_active"]
        status="ACTIVE" if student.is_active else "WITHDRAWN"
        db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="REACTIVATED" if student.is_active else "WITHDRAWN",details=f"from={previous};to={status};source=students",actor_user_id=user.id))
    audit(db,user,"UPDATE","student",f"student={student.id};fields={','.join(data.keys())}")
    db.commit()
    return {"id":student.id,"name":student.name,"email":student.email,"campus_id":student.campus_id,"status":"Active" if student.is_active else "Withdrawn"}

@app.get("/api/v1/admissions/summary")
def admission_summary(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Student")).all()
    active=sum(1 for x in students if x.is_active); withdrawn=len(students)-active
    without_section=0; without_guardian=0
    for student in students:
        section=db.scalar(select(AcademicAssignment.id).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==student.id,AcademicAssignment.assignment_type=="SECTION_ASSIGNMENT",AcademicAssignment.status=="Active"))
        if not section: without_section+=1
        guardian=db.scalar(select(ParentStudentLink.id).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.student_user_id==student.id))
        if not guardian: without_guardian+=1
    return {"total":len(students),"active":active,"withdrawn":withdrawn,"without_section":without_section,"without_guardian":without_guardian}

@app.get("/api/v1/admissions/students")
def admission_students(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Student").order_by(User.name)).all()
    result=[]
    for student in students:
        assignments=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==student.id,AcademicAssignment.status=="Active")).all()
        details=[]
        for a in assignments:
            unit=db.get(AcademicUnit,a.unit_id)
            if unit: details.append({"id":a.id,"assignment_type":a.assignment_type,"unit_id":unit.id,"unit_name":unit.name,"unit_type":unit.unit_type})
        guardian_link=db.scalar(select(ParentStudentLink.id).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.student_user_id==student.id))
        result.append({"id":student.id,"name":student.name,"email":student.email,"campus_id":student.campus_id,"status":"Active" if student.is_active else "Withdrawn","assignments":details,"has_guardian":bool(guardian_link)})
    return result

@app.get("/api/v1/admissions/students/{student_id}/profile")
def admission_student_profile(student_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    assignments=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==student.id,AcademicAssignment.status=="Active")).all()
    academics=[]
    for row in assignments:
        unit=db.get(AcademicUnit,row.unit_id)
        if unit: academics.append({"assignment_type":row.assignment_type,"unit_id":unit.id,"unit_name":unit.name,"unit_type":unit.unit_type})
    links=db.scalars(select(ParentStudentLink).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.student_user_id==student.id)).all()
    guardians=[]
    for link in links:
        parent=db.get(User,link.parent_user_id)
        if parent and parent.tenant_id==user.tenant_id:
            guardians.append({"id":parent.id,"name":parent.name,"email":parent.email,"relationship":link.relationship,"is_active":parent.is_active})
    history_count=db.scalar(select(func.count(EnrollmentHistory.id)).where(EnrollmentHistory.tenant_id==user.tenant_id,EnrollmentHistory.student_user_id==student.id)) or 0
    return {"id":student.id,"name":student.name,"email":student.email,"campus_id":student.campus_id,"status":"Active" if student.is_active else "Withdrawn","academics":academics,"guardians":guardians,"history_count":history_count}

@app.get("/api/v1/student/profile")
def student_profile(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    assignments=db.scalars(select(AcademicAssignment).where(
        AcademicAssignment.tenant_id==user.tenant_id,
        AcademicAssignment.user_id==user.id,
        AcademicAssignment.status=="Active",
    )).all()
    academics=[]
    for row in assignments:
        unit=db.get(AcademicUnit,row.unit_id)
        if unit and unit.tenant_id==user.tenant_id:
            academics.append({
                "assignment_type":row.assignment_type,
                "unit_id":unit.id,
                "unit_name":unit.name,
                "unit_code":unit.code,
                "unit_type":unit.unit_type,
            })
    links=db.scalars(select(ParentStudentLink).where(
        ParentStudentLink.tenant_id==user.tenant_id,
        ParentStudentLink.student_user_id==user.id,
    )).all()
    guardians=[]
    for link in links:
        parent=db.get(User,link.parent_user_id)
        if parent and parent.tenant_id==user.tenant_id:
            guardians.append({
                "name":parent.name,
                "relationship":link.relationship,
            })
    return {
        "id":user.id,
        "name":user.name,
        "email":user.email,
        "campus_id":user.campus_id,
        "campus_name":(db.get(AcademicUnit,user.campus_id).name if user.campus_id and db.get(AcademicUnit,user.campus_id) and db.get(AcademicUnit,user.campus_id).tenant_id==user.tenant_id else None),
        "status":"Active" if user.is_active else "Withdrawn",
        "academics":academics,
        "guardians":guardians,
    }

@app.get("/api/v1/student/grievances")
def student_grievances(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    rows=db.scalars(select(Grievance).where(
        Grievance.tenant_id==user.tenant_id,
        Grievance.created_by_user_id==user.id,
    ).order_by(Grievance.created_at.desc())).all()
    return [{"id":x.id,"ticket_no":x.ticket_no,"category":x.category,"subject":x.subject,
             "details":x.details,"priority":x.priority,"status":x.status,
             "latest_update":x.latest_update,"created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.post("/api/v1/student/grievances")
def create_student_grievance(payload:GrievanceIn,user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    subject=payload.subject.strip()
    details=payload.details.strip()
    category=payload.category.strip() or "General"
    priority=payload.priority.strip().title() or "Normal"
    if not subject: raise HTTPException(400,"subject is required")
    if not details: raise HTTPException(400,"details are required")
    if priority not in {"Low","Normal","High","Urgent"}: raise HTTPException(400,"Invalid priority")
    row=Grievance(tenant_id=user.tenant_id,campus_id=user.campus_id,created_by_user_id=user.id,
                  ticket_no="PENDING",category=category,subject=subject,details=details,priority=priority)
    db.add(row); db.flush()
    row.ticket_no=f"GR-{row.id:06d}"
    audit(db,user,"CREATE","Grievance",f"ticket={row.ticket_no};category={category};priority={priority}")
    db.commit(); db.refresh(row)
    return {"id":row.id,"ticket_no":row.ticket_no,"category":row.category,"subject":row.subject,
            "priority":row.priority,"status":row.status,"latest_update":row.latest_update,
            "created_at":row.created_at,"updated_at":row.updated_at}

@app.get("/api/v1/hr/leave")
def hr_leave_requests(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(TeacherLeaveRequest).where(TeacherLeaveRequest.tenant_id==user.tenant_id).order_by(TeacherLeaveRequest.created_at.desc())).all()
    teachers={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Teacher")).all()}
    return [{"id":x.id,"teacher_user_id":x.teacher_user_id,"teacher_name":teachers[x.teacher_user_id].name if x.teacher_user_id in teachers else "Unknown","leave_type":x.leave_type,"start_date":x.start_date,"end_date":x.end_date,"reason":x.reason,"status":x.status,"reviewer_note":x.reviewer_note,"created_at":x.created_at} for x in rows]

@app.patch("/api/v1/hr/leave/{leave_id}")
def review_hr_leave(leave_id:int,payload:HRLeaveReviewIn,user:User=Depends(require_roles("HR","Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(TeacherLeaveRequest,leave_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Leave request not found")
    if row.status!="PENDING": raise HTTPException(409,"Leave request has already been reviewed")
    status=payload.status.strip().upper()
    if status not in {"APPROVED","REJECTED"}: raise HTTPException(400,"Status must be APPROVED or REJECTED")
    if status=="REJECTED" and len(payload.reviewer_note.strip())<2: raise HTTPException(400,"Reviewer note is required when rejecting leave")
    row.status=status;row.reviewer_user_id=user.id;row.reviewer_note=payload.reviewer_note.strip();row.updated_at=dt.datetime.utcnow()
    audit(db,user,"REVIEW","teacher_leave",f"leave={row.id};teacher={row.teacher_user_id};status={status}");db.commit();db.refresh(row)
    return {"id":row.id,"status":row.status,"reviewer_note":row.reviewer_note,"updated_at":row.updated_at}

@app.get("/api/v1/teacher/leave")
def teacher_leave_requests(user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    rows=db.scalars(select(TeacherLeaveRequest).where(
        TeacherLeaveRequest.tenant_id==user.tenant_id,
        TeacherLeaveRequest.teacher_user_id==user.id,
    ).order_by(TeacherLeaveRequest.created_at.desc())).all()
    return [{"id":x.id,"leave_type":x.leave_type,"start_date":x.start_date,"end_date":x.end_date,
             "reason":x.reason,"status":x.status,"reviewer_note":x.reviewer_note,
             "created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.post("/api/v1/teacher/leave")
def create_teacher_leave(payload:TeacherLeaveIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    try:
        start=dt.datetime.fromisoformat(payload.start_date)
        end=dt.datetime.fromisoformat(payload.end_date)
    except ValueError:
        raise HTTPException(400,"Invalid leave date")
    if end < start: raise HTTPException(400,"Leave end date cannot be before start date")
    overlap=db.scalar(select(TeacherLeaveRequest).where(TeacherLeaveRequest.tenant_id==user.tenant_id,TeacherLeaveRequest.teacher_user_id==user.id,TeacherLeaveRequest.status.in_(["PENDING","APPROVED"]),TeacherLeaveRequest.start_date<=end,TeacherLeaveRequest.end_date>=start))
    if overlap: raise HTTPException(409,"A pending or approved leave request already overlaps these dates")
    leave_type=payload.leave_type.strip().title()
    if leave_type not in {"Casual","Sick","Earned","Emergency","Other"}:
        raise HTTPException(400,"Invalid leave type")
    row=TeacherLeaveRequest(tenant_id=user.tenant_id,teacher_user_id=user.id,leave_type=leave_type,
                            start_date=start,end_date=end,reason=payload.reason.strip())
    db.add(row); audit(db,user,"CREATE","Leave",leave_type); db.commit(); db.refresh(row)
    return {"id":row.id,"leave_type":row.leave_type,"start_date":row.start_date,"end_date":row.end_date,
            "reason":row.reason,"status":row.status,"reviewer_note":row.reviewer_note,"created_at":row.created_at}

@app.get("/api/v1/student/leave")
def student_leave_requests(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    rows=db.scalars(select(StudentLeaveRequest).where(StudentLeaveRequest.tenant_id==user.tenant_id,StudentLeaveRequest.student_user_id==user.id).order_by(StudentLeaveRequest.created_at.desc())).all()
    return [{"id":x.id,"leave_type":x.leave_type,"start_date":x.start_date,"end_date":x.end_date,"reason":x.reason,"status":x.status,"reviewer_note":x.reviewer_note,"created_at":x.created_at} for x in rows]

@app.post("/api/v1/student/leave")
def create_student_leave(payload:TeacherLeaveIn,user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    try:
        start=dt.datetime.fromisoformat(payload.start_date); end=dt.datetime.fromisoformat(payload.end_date)
    except ValueError: raise HTTPException(400,"Invalid leave date")
    if end<start: raise HTTPException(400,"Leave end date cannot be before start date")
    overlap=db.scalar(select(StudentLeaveRequest).where(StudentLeaveRequest.tenant_id==user.tenant_id,StudentLeaveRequest.student_user_id==user.id,StudentLeaveRequest.status.in_(["PENDING","APPROVED"]),StudentLeaveRequest.start_date<=end,StudentLeaveRequest.end_date>=start))
    if overlap: raise HTTPException(409,"A pending or approved leave request already overlaps these dates")
    leave_type=payload.leave_type.strip().title()
    if leave_type not in {"Casual","Sick","Emergency","Other"}: raise HTTPException(400,"Invalid leave type")
    reason=payload.reason.strip()
    if len(reason)<2: raise HTTPException(400,"Leave reason is required")
    row=StudentLeaveRequest(tenant_id=user.tenant_id,student_user_id=user.id,requested_by_user_id=user.id,leave_type=leave_type,start_date=start,end_date=end,reason=reason,status="PENDING")
    db.add(row); audit(db,user,"CREATE","Student Leave",leave_type); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.post("/api/v1/student/events/{event_id}/register")
def register_student_event(event_id:int,user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    event=db.scalar(select(AcademyEvent).where(AcademyEvent.id==event_id,AcademyEvent.tenant_id==user.tenant_id,AcademyEvent.status=="Published"))
    if not event or (event.campus_id is not None and event.campus_id!=user.campus_id) or event.audience_role not in ("ALL","Student"):
        raise HTTPException(404,"Event not available")
    if not event.registration_required: raise HTTPException(409,"Registration is not required for this event")
    if event.registration_deadline and event.registration_deadline<dt.datetime.utcnow(): raise HTTPException(409,"Event registration is closed")
    existing=db.scalar(select(EventRegistration).where(EventRegistration.tenant_id==user.tenant_id,EventRegistration.event_id==event.id,EventRegistration.user_id==user.id))
    if existing: return {"id":existing.id,"status":existing.status}
    row=EventRegistration(tenant_id=user.tenant_id,event_id=event.id,user_id=user.id,status="Registered")
    db.add(row); audit(db,user,"REGISTER","Events",event.title); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/parents/leave")
def parent_leave_requests(user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    child_ids={x["id"] for x in parent_children(user,db)}
    rows=db.scalars(select(StudentLeaveRequest).where(
        StudentLeaveRequest.tenant_id==user.tenant_id,
        StudentLeaveRequest.requested_by_user_id==user.id,
    ).order_by(StudentLeaveRequest.created_at.desc())).all()
    result=[]
    for row in rows:
        if row.student_user_id not in child_ids: continue
        student=db.get(User,row.student_user_id)
        result.append({"id":row.id,"student_user_id":row.student_user_id,"student_name":student.name if student else "Student",
                       "leave_type":row.leave_type,"start_date":row.start_date,"end_date":row.end_date,
                       "reason":row.reason,"status":row.status,"reviewer_note":row.reviewer_note,"created_at":row.created_at})
    return result

@app.post("/api/v1/parents/leave")
def create_parent_leave(payload:ParentStudentLeaveIn,user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    student=_linked_child(db,user,payload.student_user_id)
    try:
        start=dt.datetime.fromisoformat(payload.start_date); end=dt.datetime.fromisoformat(payload.end_date)
    except ValueError: raise HTTPException(400,"Invalid leave date")
    if end<start: raise HTTPException(400,"Leave end date cannot be before start date")
    leave_type=payload.leave_type.strip().title()
    if leave_type not in {"Casual","Sick","Emergency","Other"}: raise HTTPException(400,"Invalid leave type")
    row=StudentLeaveRequest(tenant_id=user.tenant_id,student_user_id=student.id,requested_by_user_id=user.id,
                            leave_type=leave_type,start_date=start,end_date=end,reason=payload.reason.strip(),status="PENDING")
    db.add(row); audit(db,user,"CREATE","Student Leave",f"student={student.id};type={leave_type}"); db.commit(); db.refresh(row)
    return {"id":row.id,"student_user_id":student.id,"student_name":student.name,"leave_type":row.leave_type,
            "start_date":row.start_date,"end_date":row.end_date,"reason":row.reason,"status":row.status,
            "reviewer_note":row.reviewer_note,"created_at":row.created_at}

@app.get("/api/v1/parents/grievances")
def parent_grievances(user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    rows=db.scalars(select(Grievance).where(
        Grievance.tenant_id==user.tenant_id,Grievance.created_by_user_id==user.id
    ).order_by(Grievance.created_at.desc())).all()
    return [{"id":x.id,"ticket_no":x.ticket_no,"category":x.category,"subject":x.subject,"details":x.details,
             "priority":x.priority,"status":x.status,"latest_update":x.latest_update,
             "created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.post("/api/v1/parents/grievances")
def create_parent_grievance(payload:GrievanceIn,user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    category=payload.category.strip() or "General"
    priority=payload.priority.strip().title()
    if priority not in {"Low","Normal","High","Urgent"}: raise HTTPException(400,"Invalid grievance priority")
    row=Grievance(tenant_id=user.tenant_id,campus_id=user.campus_id or 1,created_by_user_id=user.id,
                  ticket_no="PENDING",category=category,subject=payload.subject.strip(),details=payload.details.strip(),
                  priority=priority,status="Open")
    db.add(row); db.flush(); row.ticket_no=f"GR-{row.id:06d}"
    audit(db,user,"CREATE","Grievance",row.ticket_no); db.commit(); db.refresh(row)
    return {"id":row.id,"ticket_no":row.ticket_no,"category":row.category,"subject":row.subject,
            "details":row.details,"priority":row.priority,"status":row.status,"latest_update":row.latest_update,
            "created_at":row.created_at}

@app.get("/api/v1/parents/events")
def parent_events(user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    children=parent_children(user,db)
    campus_ids=set()
    for child in children:
        student=db.get(User,child["id"])
        if student and student.campus_id is not None:
            campus_ids.add(student.campus_id)
    events=db.scalars(select(AcademyEvent).where(
        AcademyEvent.tenant_id==user.tenant_id,AcademyEvent.status=="Published"
    ).order_by(AcademyEvent.starts_at.asc())).all()
    result=[]
    for event in events:
        if event.audience_role not in ("ALL","Parent / Guardian","Parent"): continue
        if event.campus_id is not None and event.campus_id not in campus_ids: continue
        organizer=db.get(User,event.organizer_user_id) if event.organizer_user_id else None
        result.append({"id":event.id,"title":event.title,"event_type":event.event_type,"venue":event.venue,
                       "starts_at":event.starts_at,"ends_at":event.ends_at,
                       "organizer":organizer.name if organizer and organizer.tenant_id==user.tenant_id else None,
                       "registration_required":event.registration_required,
                       "registration_deadline":event.registration_deadline,"status":event.status})
    return result

@app.get("/api/v1/teacher/events")
def teacher_events(user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    events=db.scalars(select(AcademyEvent).where(
        AcademyEvent.tenant_id==user.tenant_id,
        AcademyEvent.status=="Published",
    ).order_by(AcademyEvent.starts_at.asc())).all()
    result=[]
    for event in events:
        if event.campus_id is not None and event.campus_id!=user.campus_id: continue
        if event.audience_role not in ("ALL","Teacher"): continue
        organizer=db.get(User,event.organizer_user_id) if event.organizer_user_id else None
        registration=db.scalar(select(EventRegistration).where(
            EventRegistration.tenant_id==user.tenant_id,
            EventRegistration.event_id==event.id,
            EventRegistration.user_id==user.id,
        ))
        result.append({"id":event.id,"title":event.title,"event_type":event.event_type,
                       "venue":event.venue,"starts_at":event.starts_at,"ends_at":event.ends_at,
                       "organizer":organizer.name if organizer and organizer.tenant_id==user.tenant_id else None,
                       "registration_required":event.registration_required,
                       "registration_deadline":event.registration_deadline,
                       "registration_status":registration.status if registration else ("Not Registered" if event.registration_required else "Not Required"),
                       "status":event.status})
    return result

@app.post("/api/v1/teacher/events/{event_id}/register")
def register_teacher_event(event_id:int,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    event=db.scalar(select(AcademyEvent).where(AcademyEvent.id==event_id,AcademyEvent.tenant_id==user.tenant_id,AcademyEvent.status=="Published"))
    if not event or (event.campus_id is not None and event.campus_id!=user.campus_id) or event.audience_role not in ("ALL","Teacher"):
        raise HTTPException(404,"Event not available")
    if not event.registration_required: raise HTTPException(409,"Registration is not required for this event")
    if event.registration_deadline and event.registration_deadline<dt.datetime.utcnow(): raise HTTPException(409,"Event registration is closed")
    existing=db.scalar(select(EventRegistration).where(EventRegistration.tenant_id==user.tenant_id,EventRegistration.event_id==event.id,EventRegistration.user_id==user.id))
    if existing: return {"id":existing.id,"status":existing.status}
    row=EventRegistration(tenant_id=user.tenant_id,event_id=event.id,user_id=user.id,status="Registered")
    db.add(row); audit(db,user,"REGISTER","Events",event.title); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/student/events")
def student_events(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    events=db.scalars(select(AcademyEvent).where(
        AcademyEvent.tenant_id==user.tenant_id,
        AcademyEvent.status=="Published",
    ).order_by(AcademyEvent.starts_at.asc())).all()
    result=[]
    for event in events:
        if event.campus_id is not None and event.campus_id!=user.campus_id:
            continue
        if event.audience_role not in ("ALL","Student"):
            continue
        organizer=db.get(User,event.organizer_user_id) if event.organizer_user_id else None
        registration=db.scalar(select(EventRegistration).where(
            EventRegistration.tenant_id==user.tenant_id,
            EventRegistration.event_id==event.id,
            EventRegistration.user_id==user.id,
        ))
        result.append({
            "id":event.id,"title":event.title,"event_type":event.event_type,
            "venue":event.venue,"starts_at":event.starts_at,"ends_at":event.ends_at,
            "organizer":organizer.name if organizer and organizer.tenant_id==user.tenant_id else None,
            "registration_required":event.registration_required,
            "registration_deadline":event.registration_deadline,
            "registration_status":registration.status if registration else ("Not Registered" if event.registration_required else "Not Required"),
            "status":event.status,
        })
    return result

@app.get("/api/v1/student/library")
def student_library(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    loans=db.scalars(select(LibraryLoan).where(
        LibraryLoan.tenant_id==user.tenant_id,
        LibraryLoan.borrower_user_id==user.id,
    ).order_by(LibraryLoan.issued_at.desc())).all()
    result=[]
    for loan in loans:
        book=db.get(LibraryBook,loan.book_id)
        if not book or book.tenant_id!=user.tenant_id:
            continue
        result.append({
            "loan_id":loan.id,
            "book":{"id":book.id,"accession_no":book.accession_no,"isbn":book.isbn,"title":book.title,"author":book.author,"category":book.category},
            "issued_at":loan.issued_at,
            "due_at":loan.due_at,
            "returned_at":loan.returned_at,
            "fine_amount":float(loan.fine_amount or 0),
            "status":loan.status,
        })
    return result

@app.get("/api/v1/student/transport")
def student_transport(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    allocation=db.scalar(select(StudentTransportAllocation).where(
        StudentTransportAllocation.tenant_id==user.tenant_id,
        StudentTransportAllocation.student_user_id==user.id,
        StudentTransportAllocation.status=="Active",
    ))
    if not allocation:
        return {"allocated":False}
    route=db.get(TransportRoute,allocation.route_id)
    stop=db.get(TransportStop,allocation.stop_id)
    vehicle=db.get(TransportVehicle,allocation.vehicle_id) if allocation.vehicle_id else None
    if not route or route.tenant_id!=user.tenant_id or not stop or stop.tenant_id!=user.tenant_id:
        raise HTTPException(409,"Transport allocation references unavailable route or stop")
    if vehicle and vehicle.tenant_id!=user.tenant_id:
        raise HTTPException(409,"Transport allocation references unavailable vehicle")
    return {
        "allocated":True,
        "route":{"id":route.id,"name":route.name,"code":route.code},
        "vehicle":{"id":vehicle.id,"vehicle_number":vehicle.vehicle_number,"label":vehicle.label} if vehicle else None,
        "stop":{"id":stop.id,"name":stop.name,"stop_order":stop.stop_order},
        "pickup_time":allocation.pickup_time,
        "drop_time":allocation.drop_time,
        "status":allocation.status,
    }

@app.get("/api/v1/admissions/students/{student_id}/history")
def admission_history(student_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    rows=db.scalars(select(EnrollmentHistory).where(EnrollmentHistory.tenant_id==user.tenant_id,EnrollmentHistory.student_user_id==student.id).order_by(EnrollmentHistory.created_at.desc())).all()
    result=[]
    for row in rows:
        before=db.get(AcademicUnit,row.from_unit_id) if row.from_unit_id else None; after=db.get(AcademicUnit,row.to_unit_id) if row.to_unit_id else None; actor=db.get(User,row.actor_user_id)
        result.append({"id":row.id,"event_type":row.event_type,"from_unit":before.name if before else None,"to_unit":after.name if after else None,"details":row.details,"actor":actor.name if actor else "Unknown","created_at":row.created_at})
    return result

@app.patch("/api/v1/admissions/students/{student_id}")
def update_admission(student_id:int,payload:StudentEnrollmentUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,student_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student": raise HTTPException(404,"Student not found")
    data=payload.model_dump(exclude_unset=True)
    if "section_unit_id" in data and data["section_unit_id"] is not None:
        section=db.get(AcademicUnit,data["section_unit_id"])
        if not section or section.tenant_id!=user.tenant_id or section.unit_type!="SECTION_BATCH": raise HTTPException(400,"Invalid section or batch")
        old=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==student.id,AcademicAssignment.assignment_type=="SECTION_ASSIGNMENT")).all()
        previous_unit_id=old[0].unit_id if old else None
        for row in old: db.delete(row)
        db.add(AcademicAssignment(tenant_id=user.tenant_id,user_id=student.id,unit_id=section.id,assignment_type="SECTION_ASSIGNMENT",status="Active"))
        db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="SECTION_TRANSFER",from_unit_id=previous_unit_id,to_unit_id=section.id,details="",actor_user_id=user.id))
        audit(db,user,"UPDATE","student_enrollment",f"student={student.id};section={section.id}")
    if "status" in data:
        status=(data["status"] or "").strip().upper()
        if status not in {"ACTIVE","WITHDRAWN"}: raise HTTPException(400,"Status must be Active or Withdrawn")
        previous="ACTIVE" if student.is_active else "WITHDRAWN"
        student.is_active=status=="ACTIVE"
        if previous!=status:
            db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="REACTIVATED" if status=="ACTIVE" else "WITHDRAWN",details=f"from={previous};to={status}",actor_user_id=user.id))
        audit(db,user,"UPDATE","student_enrollment",f"student={student.id};status={status}")
    db.commit()
    return {"ok":True,"student_id":student.id,"status":"Active" if student.is_active else "Withdrawn"}

@app.post("/api/v1/admissions/enroll-student")
def enroll_student(payload:StudentEnrollmentIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    email=payload.email.strip().lower()
    if db.scalar(select(User).where(User.email==email)): raise HTTPException(409,"Email address is already registered")
    password=payload.password
    if not (any(x.isalpha() for x in password) and any(x.isdigit() for x in password) and any(not x.isalnum() for x in password)):
        raise HTTPException(400,"Password must contain a letter, number and special character")
    program=db.get(AcademicUnit,payload.program_unit_id)
    if not program or program.tenant_id!=user.tenant_id or program.unit_type not in {"PROGRAM","ACADEMIC_PERIOD"}: raise HTTPException(400,"Invalid program or academic period")
    section=None
    if payload.section_unit_id is not None:
        section=db.get(AcademicUnit,payload.section_unit_id)
        if not section or section.tenant_id!=user.tenant_id or section.unit_type!="SECTION_BATCH": raise HTTPException(400,"Invalid section or batch")
    courses=[]
    for unit_id in dict.fromkeys(payload.course_unit_ids):
        unit=db.get(AcademicUnit,unit_id)
        if not unit or unit.tenant_id!=user.tenant_id or unit.unit_type!="COURSE": raise HTTPException(400,"Invalid course")
        courses.append(unit)
    parent=None
    if payload.parent_user_id is not None:
        parent=db.get(User,payload.parent_user_id)
        if not parent or parent.tenant_id!=user.tenant_id or parent.role!="Parent / Guardian" or not parent.is_active: raise HTTPException(400,"Invalid parent or guardian")
    student=User(email=email,name=payload.name.strip(),role="Student",password_hash=hash_password(password),tenant_id=user.tenant_id,campus_id=payload.campus_id,is_active=True)
    db.add(student); db.flush()
    assignments=[AcademicAssignment(tenant_id=user.tenant_id,user_id=student.id,unit_id=program.id,assignment_type="ENROLLMENT",status="Active")]
    if section: assignments.append(AcademicAssignment(tenant_id=user.tenant_id,user_id=student.id,unit_id=section.id,assignment_type="SECTION_ASSIGNMENT",status="Active"))
    assignments.extend(AcademicAssignment(tenant_id=user.tenant_id,user_id=student.id,unit_id=x.id,assignment_type="COURSE_REGISTRATION",status="Active") for x in courses)
    db.add_all(assignments)
    if parent: db.add(ParentStudentLink(parent_user_id=parent.id,student_user_id=student.id,relationship=payload.relationship.strip(),tenant_id=user.tenant_id))
    db.add(EnrollmentHistory(tenant_id=user.tenant_id,student_user_id=student.id,event_type="ENROLLED",to_unit_id=program.id,details=f"section={section.id if section else ''};courses={len(courses)};parent={parent.id if parent else ''}",actor_user_id=user.id))
    audit(db,user,"CREATE","student_enrollment",f"student={student.id};program={program.id};section={section.id if section else ''};courses={len(courses)};parent={parent.id if parent else ''}")
    db.commit(); db.refresh(student)
    return {"id":student.id,"name":student.name,"email":student.email,"program":program.name,"section":section.name if section else None,"courses":[x.name for x in courses],"parent_linked":bool(parent)}

@app.get("/api/v1/academic-assignments")
def academic_assignments(user:User=Depends(current_user),db:Session=Depends(get_db)):
    st=select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id)
    if user.role in {"Student","Teacher"}: st=st.where(AcademicAssignment.user_id==user.id)
    elif user.role not in {"Institution Admin","Campus Admin","Auditor"}: raise HTTPException(403,"Academic assignments are not available for your role")
    rows=db.scalars(st.order_by(AcademicAssignment.id.desc())).all()
    result=[]
    for r in rows:
        assigned=db.get(User,r.user_id); unit=db.get(AcademicUnit,r.unit_id)
        if assigned and unit:
            result.append({"id":r.id,"user_id":r.user_id,"user_name":assigned.name,"user_role":assigned.role,"unit_id":r.unit_id,"unit_name":unit.name,"unit_type":unit.unit_type,"assignment_type":r.assignment_type,"status":r.status})
    return result

@app.post("/api/v1/academic-assignments")
def create_academic_assignment(payload:AcademicAssignmentIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    assigned=db.get(User,payload.user_id); unit=db.get(AcademicUnit,payload.unit_id)
    if not assigned or assigned.tenant_id!=user.tenant_id: raise HTTPException(400,"Invalid user")
    if assigned.role not in {"Student","Teacher"}: raise HTTPException(400,"Only Student or Teacher users can receive academic assignments")
    if not unit or unit.tenant_id!=user.tenant_id: raise HTTPException(400,"Invalid academic unit")
    assignment_type=payload.assignment_type.strip().upper()
    allowed={"ENROLLMENT","COURSE_REGISTRATION","SECTION_ASSIGNMENT","FACULTY_ASSIGNMENT","ADVISOR_ASSIGNMENT"}
    if assignment_type not in allowed: raise HTTPException(400,"Unsupported assignment type")

    student_rules={
        "ENROLLMENT":{"PROGRAM","ACADEMIC_PERIOD"},
        "COURSE_REGISTRATION":{"COURSE"},
        "SECTION_ASSIGNMENT":{"SECTION_BATCH"},
    }
    teacher_rules={
        "FACULTY_ASSIGNMENT":{"COURSE","SECTION_BATCH"},
        "ADVISOR_ASSIGNMENT":{"PROGRAM","SECTION_BATCH"},
    }
    role_rules=student_rules if assigned.role=="Student" else teacher_rules
    if assignment_type not in role_rules:
        raise HTTPException(400,f"{assignment_type} is not valid for role {assigned.role}")
    if unit.unit_type not in role_rules[assignment_type]:
        expected=", ".join(sorted(role_rules[assignment_type]))
        raise HTTPException(400,f"{assignment_type} requires academic unit type: {expected}")

    existing=db.scalar(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==assigned.id,AcademicAssignment.unit_id==unit.id,AcademicAssignment.assignment_type==assignment_type))
    if existing: raise HTTPException(409,"This academic assignment already exists")
    row=AcademicAssignment(tenant_id=user.tenant_id,user_id=assigned.id,unit_id=unit.id,assignment_type=assignment_type,status=payload.status)
    db.add(row); audit(db,user,"CREATE","academic_assignment",f"{assigned.email}:{assignment_type}:{unit.code}"); db.commit(); db.refresh(row)
    return {"id":row.id,"user_name":assigned.name,"unit_name":unit.name,"assignment_type":row.assignment_type,"status":row.status}

@app.delete("/api/v1/academic-assignments/{assignment_id}")
def delete_academic_assignment(assignment_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(AcademicAssignment,assignment_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Academic assignment not found")
    audit(db,user,"DELETE","academic_assignment",str(row.id)); db.delete(row); db.commit()
    return {"ok":True}

@app.get("/api/v1/navigation")
def navigation(user: User = Depends(current_user)):
    return {"role":user.role,"items":ROLE_MENUS.get(user.role,["Dashboard"])}

@app.get("/api/v1/module-access/{page:path}")
def module_access(page: str, user: User = Depends(current_user)):
    result = module_access_for(user.role, page)
    if not result["can_view"]:
        raise HTTPException(403, "This module is not available for your role")
    return result

@app.get("/api/v1/dashboard")
def dashboard(user: User = Depends(current_user)):
    return dashboard_for(user.role)

@app.get("/api/v1/campus/dashboard")
def campus_dashboard(user:User=Depends(require_roles("Campus Admin","Institution Admin")),db:Session=Depends(get_db)):
    if user.campus_id is None: raise HTTPException(400,"A campus assignment is required for campus operations")
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role=="Student")).all()
    staff_roles={"Teacher","Accounts","HR","Campus Admin","Auditor"}
    staff=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role.in_(staff_roles))).all()
    return {"campus_id":user.campus_id,"students":{"total":len(students),"active":sum(1 for x in students if x.is_active)},"staff":{"total":len(staff),"active":sum(1 for x in staff if x.is_active)}}

@app.get("/api/v1/campus/students")
def campus_students(user:User=Depends(require_roles("Campus Admin","Institution Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role=="Student").order_by(User.name)).all()
    return [{"id":x.id,"name":x.name,"email":x.email,"campus_id":x.campus_id,"is_active":x.is_active} for x in rows]

@app.get("/api/v1/campus/staff")
def campus_staff(user:User=Depends(require_roles("Campus Admin","Institution Admin")),db:Session=Depends(get_db)):
    roles={"Teacher","Accounts","HR","Campus Admin","Auditor"}
    rows=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role.in_(roles)).order_by(User.name)).all()
    return [{"id":x.id,"name":x.name,"email":x.email,"role":x.role,"campus_id":x.campus_id,"is_active":x.is_active} for x in rows]

@app.get("/api/v1/campus/attendance")
def campus_attendance(user:User=Depends(require_roles("Campus Admin","Institution Admin")),db:Session=Depends(get_db)):
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role=="Student")).all()
    ids={x.id for x in students}
    entries=db.scalars(select(AttendanceEntry).where(AttendanceEntry.tenant_id==user.tenant_id).order_by(AttendanceEntry.marked_at.desc())).all()
    entries=[x for x in entries if x.student_user_id in ids]
    names={x.id:x.name for x in students}
    counts={}
    for x in entries: counts[x.status]=counts.get(x.status,0)+1
    return {"summary":{"total_records":len(entries),"present":counts.get("PRESENT",0),"absent":counts.get("ABSENT",0),"late":counts.get("LATE",0)},"entries":[{"id":x.id,"student_user_id":x.student_user_id,"student_name":names.get(x.student_user_id,""),"session_id":x.session_id,"status":x.status,"note":x.note,"marked_at":x.marked_at} for x in entries[:200]]}

@app.get("/api/v1/campus/transport")
def campus_transport(user:User=Depends(require_roles("Campus Admin","Institution Admin")),db:Session=Depends(get_db)):
    routes=db.scalars(select(TransportRoute).where(TransportRoute.tenant_id==user.tenant_id,TransportRoute.campus_id==user.campus_id).order_by(TransportRoute.name)).all()
    vehicles=db.scalars(select(TransportVehicle).where(TransportVehicle.tenant_id==user.tenant_id,TransportVehicle.campus_id==user.campus_id).order_by(TransportVehicle.vehicle_number)).all()
    allocations=db.scalars(select(StudentTransportAllocation).where(StudentTransportAllocation.tenant_id==user.tenant_id,StudentTransportAllocation.campus_id==user.campus_id)).all()
    route_names={x.id:x.name for x in routes}; vehicle_names={x.id:x.vehicle_number for x in vehicles}
    student_ids={x.student_user_id for x in allocations}
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.id.in_(student_ids))).all() if student_ids else []
    names={x.id:x.name for x in students}
    campuses=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.unit_type=="CAMPUS",AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    units=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    unit_map={x.id:x for x in units}
    return {"campuses":[{"id":x.id,"name":x.name,"code":x.code} for x in campuses],"academic_units":[{"id":x.id,"name":x.name,"code":x.code,"unit_type":x.unit_type} for x in units],"summary":{"routes":len(routes),"active_routes":sum(1 for x in routes if x.status=="Active"),"vehicles":len(vehicles),"active_vehicles":sum(1 for x in vehicles if x.status=="Active"),"allocations":len(allocations)},"routes":[{"id":x.id,"name":x.name,"code":x.code,"status":x.status} for x in routes],"vehicles":[{"id":x.id,"vehicle_number":x.vehicle_number,"label":x.label,"status":x.status} for x in vehicles],"allocations":[{"id":x.id,"student_name":names.get(x.student_user_id,""),"route_name":route_names.get(x.route_id,""),"vehicle_number":vehicle_names.get(x.vehicle_id,"") if x.vehicle_id else "","pickup_time":x.pickup_time,"drop_time":x.drop_time,"status":x.status} for x in allocations]}

@app.get("/api/v1/campus/visitors")
def campus_visitors(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CampusVisitor).where(CampusVisitor.tenant_id==user.tenant_id,CampusVisitor.campus_id==user.campus_id).order_by(CampusVisitor.id.desc()).limit(200)).all()
    return [{"id":x.id,"name":x.name,"phone":x.phone,"purpose":x.purpose,"person_to_meet":x.person_to_meet,"status":x.status,"checked_in_at":x.checked_in_at,"checked_out_at":x.checked_out_at} for x in rows]

@app.post("/api/v1/campus/visitors")
def campus_visitor_checkin(payload:CampusVisitorIn,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    if user.campus_id is None: raise HTTPException(400,"A campus assignment is required for campus operations")
    if not payload.name.strip() or not payload.purpose.strip(): raise HTTPException(400,"Visitor name and purpose are required")
    row=CampusVisitor(tenant_id=user.tenant_id,campus_id=user.campus_id,recorded_by=user.id,**payload.model_dump())
    db.add(row); audit(db,user,"VISITOR_CHECK_IN","campus_visitor",payload.name); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.patch("/api/v1/campus/visitors/{visitor_id}")
def campus_visitor_status(visitor_id:int,payload:CampusVisitorStatusIn,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusVisitor).where(CampusVisitor.id==visitor_id,CampusVisitor.tenant_id==user.tenant_id,CampusVisitor.campus_id==user.campus_id))
    if not row: raise HTTPException(404,"Visitor not found")
    if payload.status!="CHECKED_OUT": raise HTTPException(400,"Only CHECKED_OUT is allowed")
    if row.status=="CHECKED_OUT": return {"id":row.id,"status":row.status}
    row.status="CHECKED_OUT"; row.checked_out_at=dt.datetime.utcnow()
    audit(db,user,"VISITOR_CHECK_OUT",f"campus_visitor:{row.id}",row.name); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/campus/inventory")
def campus_inventory(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CampusInventoryItem).where(CampusInventoryItem.tenant_id==user.tenant_id,CampusInventoryItem.campus_id==user.campus_id).order_by(CampusInventoryItem.name)).all()
    return [{"id":x.id,"name":x.name,"category":x.category,"item_code":x.item_code,"quantity":x.quantity,"minimum_quantity":x.minimum_quantity,"location":x.location,"status":x.status,"notes":x.notes} for x in rows]

@app.post("/api/v1/campus/inventory")
def campus_inventory_create(payload:CampusInventoryIn,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    if user.campus_id is None: raise HTTPException(400,"A campus assignment is required for campus operations")
    if not payload.name.strip() or not payload.item_code.strip(): raise HTTPException(400,"Inventory name and item code are required")
    if payload.quantity<0 or payload.minimum_quantity<0: raise HTTPException(400,"Inventory quantities cannot be negative")
    if payload.status not in {"ACTIVE","INACTIVE"}: raise HTTPException(400,"Invalid inventory status")
    row=CampusInventoryItem(tenant_id=user.tenant_id,campus_id=user.campus_id,recorded_by=user.id,**payload.model_dump())
    db.add(row); audit(db,user,"INVENTORY_CREATE","campus_inventory",payload.name); db.commit(); db.refresh(row)
    return {"id":row.id}

@app.patch("/api/v1/campus/inventory/{item_id}")
def campus_inventory_update(item_id:int,payload:CampusInventoryUpdate,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusInventoryItem).where(CampusInventoryItem.id==item_id,CampusInventoryItem.tenant_id==user.tenant_id,CampusInventoryItem.campus_id==user.campus_id))
    if not row: raise HTTPException(404,"Inventory item not found")
    if payload.status not in {"ACTIVE","INACTIVE"}: raise HTTPException(400,"Invalid inventory status")
    if payload.quantity<0: raise HTTPException(400,"Inventory quantity cannot be negative")
    row.quantity=payload.quantity; row.status=payload.status; row.notes=payload.notes; row.updated_at=dt.datetime.utcnow()
    audit(db,user,"INVENTORY_UPDATE",f"campus_inventory:{row.id}",f"quantity={row.quantity};status={row.status}"); db.commit()
    return {"id":row.id,"quantity":row.quantity,"status":row.status}

@app.get("/api/v1/campus/assets")
def campus_assets(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id,CampusAsset.campus_id==user.campus_id).order_by(CampusAsset.name)).all()
    return [{"id":x.id,"asset_code":x.asset_code,"name":x.name,"category":x.category,"serial_number":x.serial_number,"location":x.location,"assigned_to":x.assigned_to,"condition":x.condition,"status":x.status,"notes":x.notes} for x in rows]

@app.post("/api/v1/campus/assets")
def campus_asset_create(payload:CampusAssetIn,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    if user.campus_id is None: raise HTTPException(400,"A campus assignment is required for campus operations")
    if not payload.asset_code.strip() or not payload.name.strip(): raise HTTPException(400,"Asset code and name are required")
    if payload.condition not in {"GOOD","FAIR","DAMAGED","REPAIR"}: raise HTTPException(400,"Invalid asset condition")
    if payload.status not in {"ACTIVE","INACTIVE","RETIRED"}: raise HTTPException(400,"Invalid asset status")
    duplicate=db.scalar(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id,CampusAsset.campus_id==user.campus_id,CampusAsset.asset_code==payload.asset_code))
    if duplicate: raise HTTPException(409,"Asset code already exists in this campus")
    row=CampusAsset(tenant_id=user.tenant_id,campus_id=user.campus_id,recorded_by=user.id,**payload.model_dump())
    db.add(row); audit(db,user,"ASSET_CREATE","campus_asset",payload.asset_code); db.commit(); db.refresh(row)
    return {"id":row.id}

@app.patch("/api/v1/campus/assets/{asset_id}")
def campus_asset_update(asset_id:int,payload:CampusAssetUpdate,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusAsset).where(CampusAsset.id==asset_id,CampusAsset.tenant_id==user.tenant_id,CampusAsset.campus_id==user.campus_id))
    if not row: raise HTTPException(404,"Asset not found")
    if payload.condition not in {"GOOD","FAIR","DAMAGED","REPAIR"}: raise HTTPException(400,"Invalid asset condition")
    if payload.status not in {"ACTIVE","INACTIVE","RETIRED"}: raise HTTPException(400,"Invalid asset status")
    row.location=payload.location; row.assigned_to=payload.assigned_to; row.condition=payload.condition; row.status=payload.status; row.notes=payload.notes; row.updated_at=dt.datetime.utcnow()
    audit(db,user,"ASSET_UPDATE",f"campus_asset:{row.id}",f"condition={row.condition};status={row.status}"); db.commit()
    return {"id":row.id,"condition":row.condition,"status":row.status}

@app.get("/api/v1/campus/events")
def campus_events(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(AcademyEvent).where(AcademyEvent.tenant_id==user.tenant_id,AcademyEvent.campus_id==user.campus_id).order_by(AcademyEvent.starts_at.desc())).all()
    return [{"id":x.id,"title":x.title,"event_type":x.event_type,"venue":x.venue,"starts_at":x.starts_at,"ends_at":x.ends_at,"audience_role":x.audience_role,"registration_required":x.registration_required,"registration_deadline":x.registration_deadline,"status":x.status} for x in rows]

@app.post("/api/v1/campus/events")
def campus_event_create(payload:CampusEventIn,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    if user.campus_id is None: raise HTTPException(400,"A campus assignment is required for campus operations")
    if not payload.title.strip(): raise HTTPException(400,"Event title is required")
    try:
        starts=dt.datetime.fromisoformat(payload.starts_at); ends=dt.datetime.fromisoformat(payload.ends_at)
        deadline=dt.datetime.fromisoformat(payload.registration_deadline) if payload.registration_deadline else None
    except ValueError: raise HTTPException(400,"Invalid event date/time")
    if ends<=starts: raise HTTPException(400,"Event end must be after start")
    allowed={"ALL","Student","Teacher","Parent","Parent / Guardian"}
    if payload.audience_role not in allowed: raise HTTPException(400,"Invalid audience role")
    if deadline and deadline>starts: raise HTTPException(400,"Registration deadline must be before event start")
    row=AcademyEvent(tenant_id=user.tenant_id,campus_id=user.campus_id,title=payload.title,event_type=payload.event_type,venue=payload.venue,starts_at=starts,ends_at=ends,organizer_user_id=user.id,audience_role=payload.audience_role,registration_required=payload.registration_required,registration_deadline=deadline,status="Published")
    db.add(row); audit(db,user,"EVENT_CREATE","campus_event",payload.title); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/campus/grievances")
def campus_grievances(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id,Grievance.campus_id==user.campus_id).order_by(Grievance.created_at.desc())).all()
    creators={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id)).all()}
    return [{"id":x.id,"ticket_no":x.ticket_no,"creator_name":creators[x.created_by_user_id].name if x.created_by_user_id in creators else "User","category":x.category,"subject":x.subject,"details":x.details,"priority":x.priority,"status":x.status,"latest_update":x.latest_update,"created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.patch("/api/v1/campus/grievances/{grievance_id}")
def campus_grievance_update(grievance_id:int,payload:CampusGrievanceUpdateIn,user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(Grievance).where(Grievance.id==grievance_id,Grievance.tenant_id==user.tenant_id,Grievance.campus_id==user.campus_id))
    if not row: raise HTTPException(404,"Grievance not found")
    status=payload.status.strip().title()
    if status not in {"Open","In Progress","Resolved","Closed"}: raise HTTPException(400,"Invalid grievance status")
    row.status=status; row.latest_update=payload.latest_update.strip(); row.updated_at=dt.datetime.utcnow()
    audit(db,user,"GRIEVANCE_UPDATE",f"grievance:{row.id}",f"ticket={row.ticket_no};status={status}"); db.commit()
    return {"id":row.id,"ticket_no":row.ticket_no,"status":row.status,"latest_update":row.latest_update}

@app.get("/api/v1/campus/reports")
def campus_reports(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role=="Student")).all()
    staff_roles={"Teacher","Accounts","HR","Campus Admin","Auditor"}
    staff=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role.in_(staff_roles))).all()
    student_ids={x.id for x in students}
    attendance=db.scalars(select(AttendanceEntry).where(AttendanceEntry.tenant_id==user.tenant_id)).all()
    attendance=[x for x in attendance if x.student_user_id in student_ids]
    routes=db.scalars(select(TransportRoute).where(TransportRoute.tenant_id==user.tenant_id,TransportRoute.campus_id==user.campus_id)).all()
    vehicles=db.scalars(select(TransportVehicle).where(TransportVehicle.tenant_id==user.tenant_id,TransportVehicle.campus_id==user.campus_id)).all()
    visitors=db.scalars(select(CampusVisitor).where(CampusVisitor.tenant_id==user.tenant_id,CampusVisitor.campus_id==user.campus_id)).all()
    inventory=db.scalars(select(CampusInventoryItem).where(CampusInventoryItem.tenant_id==user.tenant_id,CampusInventoryItem.campus_id==user.campus_id)).all()
    assets=db.scalars(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id,CampusAsset.campus_id==user.campus_id)).all()
    events=db.scalars(select(AcademyEvent).where(AcademyEvent.tenant_id==user.tenant_id,AcademyEvent.campus_id==user.campus_id)).all()
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id,Grievance.campus_id==user.campus_id)).all()
    return {"campus_id":user.campus_id,
      "people":{"students":len(students),"active_students":sum(x.is_active for x in students),"staff":len(staff),"active_staff":sum(x.is_active for x in staff)},
      "attendance":{"records":len(attendance),"present":sum(x.status=="PRESENT" for x in attendance),"absent":sum(x.status=="ABSENT" for x in attendance)},
      "transport":{"routes":len(routes),"vehicles":len(vehicles)},
      "visitors":{"total":len(visitors),"inside":sum(x.status=="CHECKED_IN" for x in visitors)},
      "inventory":{"items":len(inventory),"low_stock":sum(x.quantity<=x.minimum_quantity for x in inventory)},
      "assets":{"total":len(assets),"needs_attention":sum(x.condition in {"DAMAGED","REPAIR"} for x in assets)},
      "events":{"total":len(events),"published":sum(x.status=="Published" for x in events)},
      "grievances":{"total":len(grievances),"open":sum(x.status in {"Open","In Progress"} for x in grievances),"resolved":sum(x.status in {"Resolved","Closed"} for x in grievances)}}

@app.get("/api/v1/hr/reports")
def hr_reports(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    staff_roles={"Teacher","Accounts","HR","Campus Admin","Auditor"}
    staff=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role.in_(staff_roles))).all()
    attendance=db.scalars(select(StaffAttendance).where(StaffAttendance.tenant_id==user.tenant_id)).all()
    leaves=db.scalars(select(TeacherLeaveRequest).where(TeacherLeaveRequest.tenant_id==user.tenant_id)).all()
    documents=db.scalars(select(StaffDocument).where(StaffDocument.tenant_id==user.tenant_id)).all()
    candidates=db.scalars(select(RecruitmentCandidate).where(RecruitmentCandidate.tenant_id==user.tenant_id)).all()
    reviews=db.scalars(select(StaffPerformanceReview).where(StaffPerformanceReview.tenant_id==user.tenant_id)).all()
    ratings=[x.rating for x in reviews if x.status=="COMPLETED"]
    return {
      "workforce":{"total":len(staff),"active":sum(1 for x in staff if x.is_active),"teachers":sum(1 for x in staff if x.role=="Teacher")},
      "attendance":{"total_records":len(attendance),"present":sum(1 for x in attendance if x.status=="PRESENT"),"absent":sum(1 for x in attendance if x.status=="ABSENT"),"leave":sum(1 for x in attendance if x.status=="LEAVE")},
      "leave":{"pending":sum(1 for x in leaves if x.status=="PENDING"),"approved":sum(1 for x in leaves if x.status=="APPROVED"),"rejected":sum(1 for x in leaves if x.status=="REJECTED")},
      "documents":{"total":len(documents),"active":sum(1 for x in documents if x.status=="ACTIVE"),"expired":sum(1 for x in documents if x.status=="EXPIRED")},
      "recruitment":{"total":len(candidates),"interview":sum(1 for x in candidates if x.stage=="INTERVIEW"),"offered":sum(1 for x in candidates if x.stage=="OFFERED"),"hired":sum(1 for x in candidates if x.stage=="HIRED")},
      "performance":{"reviews":len(reviews),"completed":len(ratings),"average_rating":round(sum(ratings)/len(ratings),2) if ratings else None}
    }

@app.get("/api/v1/hr/performance")
def hr_performance(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(StaffPerformanceReview).where(StaffPerformanceReview.tenant_id==user.tenant_id).order_by(StaffPerformanceReview.created_at.desc())).all()
    people={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()}
    return [{"id":x.id,"staff_user_id":x.staff_user_id,"staff_name":people[x.staff_user_id].name if x.staff_user_id in people else "Unknown","role":people[x.staff_user_id].role if x.staff_user_id in people else "","review_period":x.review_period,"rating":x.rating,"strengths":x.strengths,"improvement_areas":x.improvement_areas,"goals":x.goals,"status":x.status,"created_at":x.created_at} for x in rows]

@app.post("/api/v1/hr/performance")
def create_hr_performance(payload:StaffPerformanceReviewIn,user:User=Depends(require_roles("HR","Institution Admin")),db:Session=Depends(get_db)):
    target=db.get(User,payload.staff_user_id)
    if not target or target.tenant_id!=user.tenant_id or target.role not in {"Teacher","Accounts","HR","Campus Admin","Auditor"} or not target.is_active: raise HTTPException(400,"Invalid or inactive staff member")
    if not payload.review_period.strip(): raise HTTPException(400,"Review period is required")
    status=payload.status.strip().upper()
    if status not in {"DRAFT","COMPLETED"}: raise HTTPException(400,"Invalid review status")
    row=StaffPerformanceReview(tenant_id=user.tenant_id,staff_user_id=target.id,review_period=payload.review_period.strip(),rating=payload.rating,strengths=payload.strengths.strip(),improvement_areas=payload.improvement_areas.strip(),goals=payload.goals.strip(),status=status,reviewed_by=user.id)
    db.add(row);audit(db,user,"CREATE","staff_performance",f"staff={target.id};period={row.review_period};rating={row.rating}");db.commit();db.refresh(row)
    return {"id":row.id,"staff_user_id":row.staff_user_id,"review_period":row.review_period,"rating":row.rating,"status":row.status}

@app.get("/api/v1/hr/recruitment")
def hr_recruitment(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(RecruitmentCandidate).where(RecruitmentCandidate.tenant_id==user.tenant_id).order_by(RecruitmentCandidate.updated_at.desc())).all()
    return [{"id":x.id,"name":x.name,"email":x.email,"phone":x.phone,"position":x.position,"stage":x.stage,"source":x.source,"notes":x.notes,"created_at":x.created_at,"updated_at":x.updated_at} for x in rows]

@app.post("/api/v1/hr/recruitment")
def create_hr_candidate(payload:RecruitmentCandidateIn,user:User=Depends(require_roles("HR","Institution Admin")),db:Session=Depends(get_db)):
    email=payload.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"): raise HTTPException(400,"Invalid email address")
    stages={"APPLIED","SCREENING","INTERVIEW","OFFERED","HIRED","REJECTED","WITHDRAWN"}
    stage=payload.stage.strip().upper()
    if stage not in stages: raise HTTPException(400,"Invalid recruitment stage")
    if not payload.name.strip() or not payload.position.strip(): raise HTTPException(400,"Candidate name and position are required")
    if db.scalar(select(RecruitmentCandidate).where(RecruitmentCandidate.tenant_id==user.tenant_id,RecruitmentCandidate.email==email,RecruitmentCandidate.stage.notin_(["REJECTED","WITHDRAWN"]))): raise HTTPException(409,"An active candidate with this email already exists")
    row=RecruitmentCandidate(tenant_id=user.tenant_id,name=payload.name.strip(),email=email,phone=payload.phone.strip(),position=payload.position.strip(),stage=stage,source=payload.source.strip(),notes=payload.notes.strip(),recorded_by=user.id)
    db.add(row);audit(db,user,"CREATE","recruitment",f"candidate={email};position={row.position}");db.commit();db.refresh(row)
    return {"id":row.id,"name":row.name,"email":row.email,"position":row.position,"stage":row.stage}

@app.patch("/api/v1/hr/recruitment/{candidate_id}")
def update_hr_candidate(candidate_id:int,payload:RecruitmentStageIn,user:User=Depends(require_roles("HR","Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(RecruitmentCandidate,candidate_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Candidate not found")
    stage=payload.stage.strip().upper()
    if stage not in {"APPLIED","SCREENING","INTERVIEW","OFFERED","HIRED","REJECTED","WITHDRAWN"}: raise HTTPException(400,"Invalid recruitment stage")
    row.stage=stage
    if payload.notes is not None: row.notes=payload.notes.strip()
    row.updated_at=dt.datetime.utcnow();audit(db,user,"UPDATE","recruitment",f"candidate={row.id};stage={stage}");db.commit();db.refresh(row)
    return {"id":row.id,"stage":row.stage,"notes":row.notes,"updated_at":row.updated_at}

@app.get("/api/v1/hr/documents")
def hr_documents(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(StaffDocument).where(StaffDocument.tenant_id==user.tenant_id).order_by(StaffDocument.created_at.desc())).all()
    people={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()}
    return [{"id":x.id,"staff_user_id":x.staff_user_id,"staff_name":people[x.staff_user_id].name if x.staff_user_id in people else "Unknown","document_type":x.document_type,"title":x.title,"document_ref":x.document_ref,"expiry_date":x.expiry_date,"status":x.status,"notes":x.notes,"created_at":x.created_at} for x in rows]

@app.post("/api/v1/hr/documents")
def create_hr_document(payload:StaffDocumentIn,user:User=Depends(require_roles("HR","Institution Admin")),db:Session=Depends(get_db)):
    target=db.get(User,payload.staff_user_id)
    if not target or target.tenant_id!=user.tenant_id or target.role not in {"Teacher","Accounts","HR","Campus Admin","Auditor"} or not target.is_active: raise HTTPException(400,"Invalid or inactive staff member")
    if not payload.document_type.strip() or not payload.title.strip(): raise HTTPException(400,"Document type and title are required")
    expiry=None
    if payload.expiry_date:
        try: expiry=dt.datetime.fromisoformat(payload.expiry_date)
        except ValueError: raise HTTPException(400,"Invalid expiry date")
    status=payload.status.strip().upper()
    if status not in {"ACTIVE","PENDING","EXPIRED","ARCHIVED"}: raise HTTPException(400,"Invalid document status")
    row=StaffDocument(tenant_id=user.tenant_id,staff_user_id=target.id,document_type=payload.document_type.strip(),title=payload.title.strip(),document_ref=payload.document_ref.strip(),expiry_date=expiry,status=status,notes=payload.notes.strip(),recorded_by=user.id)
    db.add(row);audit(db,user,"CREATE","staff_document",f"staff={target.id};type={row.document_type}");db.commit();db.refresh(row)
    return {"id":row.id,"staff_user_id":row.staff_user_id,"document_type":row.document_type,"title":row.title,"status":row.status}

@app.get("/api/v1/hr/attendance")
def hr_attendance(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(StaffAttendance).where(StaffAttendance.tenant_id==user.tenant_id).order_by(StaffAttendance.attendance_date.desc(),StaffAttendance.id.desc())).all()
    users={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()}
    return [{"id":x.id,"staff_user_id":x.staff_user_id,"staff_name":users[x.staff_user_id].name if x.staff_user_id in users else "Unknown","role":users[x.staff_user_id].role if x.staff_user_id in users else "","attendance_date":x.attendance_date,"status":x.status,"note":x.note} for x in rows]

@app.post("/api/v1/hr/attendance")
def mark_hr_attendance(payload:StaffAttendanceIn,user:User=Depends(require_roles("HR","Institution Admin")),db:Session=Depends(get_db)):
    target=db.get(User,payload.staff_user_id)
    if not target or target.tenant_id!=user.tenant_id or target.role not in {"Teacher","Accounts","HR","Campus Admin","Auditor"} or not target.is_active: raise HTTPException(400,"Invalid or inactive staff member")
    try: day=dt.datetime.fromisoformat(payload.attendance_date).replace(hour=0,minute=0,second=0,microsecond=0)
    except ValueError: raise HTTPException(400,"Invalid attendance date")
    status=payload.status.strip().upper()
    if status not in {"PRESENT","ABSENT","LEAVE","HALF_DAY","WORK_FROM_HOME"}: raise HTTPException(400,"Invalid attendance status")
    row=db.scalar(select(StaffAttendance).where(StaffAttendance.tenant_id==user.tenant_id,StaffAttendance.staff_user_id==target.id,StaffAttendance.attendance_date==day))
    if row: row.status=status;row.note=payload.note.strip();row.recorded_by=user.id;row.updated_at=dt.datetime.utcnow()
    else: row=StaffAttendance(tenant_id=user.tenant_id,staff_user_id=target.id,attendance_date=day,status=status,note=payload.note.strip(),recorded_by=user.id);db.add(row)
    audit(db,user,"ATTENDANCE","staff",f"staff={target.id};date={day.date()};status={status}");db.commit();db.refresh(row)
    return {"id":row.id,"staff_user_id":row.staff_user_id,"attendance_date":row.attendance_date,"status":row.status,"note":row.note}

@app.get("/api/v1/hr/staff")
def hr_staff(user:User=Depends(require_roles("HR","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    staff_roles={"Teacher","Accounts","HR","Campus Admin","Auditor"}
    rows=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role.in_(staff_roles)).order_by(User.name)).all()
    return [{"id":x.id,"name":x.name,"email":x.email,"role":x.role,"campus_id":x.campus_id,"is_active":x.is_active} for x in rows]

@app.get("/api/v1/users")
def users(
    user: User = Depends(require_roles("Institution Admin","Campus Admin","Auditor")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(User).where(User.tenant_id==user.tenant_id).order_by(User.id)).all()
    return [
        {"id":x.id,"name":x.name,"email":x.email,"role":x.role,"campus_id":x.campus_id,"is_active":x.is_active}
        for x in rows
    ]

@app.post("/api/v1/users")
def create_user(
    payload:UserAdminCreate,
    user:User=Depends(require_roles("Institution Admin")),
    db:Session=Depends(get_db),
):
    allowed_roles={"Institution Admin","Teacher","Student","Parent / Guardian","Accounts","HR","Campus Admin","Auditor"}
    role=payload.role.strip()
    if role not in allowed_roles: raise HTTPException(400,"Unsupported role")
    email=payload.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(400,"Invalid email address")
    if db.scalar(select(User).where(User.email==email)):
        raise HTTPException(409,"Email address is already registered")
    password=payload.password
    if not (any(x.isalpha() for x in password) and any(x.isdigit() for x in password) and any(not x.isalnum() for x in password)):
        raise HTTPException(400,"Password must contain a letter, number and special character")
    target=User(email=email,name=payload.name.strip(),role=role,password_hash=hash_password(password),tenant_id=user.tenant_id,campus_id=payload.campus_id,is_active=True)
    db.add(target); db.flush()
    audit(db,user,"CREATE","user",f"user_id={target.id};role={role};campus={target.campus_id}")
    db.commit(); db.refresh(target)
    return {"id":target.id,"name":target.name,"email":target.email,"role":target.role,"campus_id":target.campus_id,"is_active":target.is_active}

@app.patch("/api/v1/users/{target_user_id}")
def update_user(
    target_user_id:int,
    payload:UserAdminUpdate,
    user:User=Depends(require_roles("Institution Admin")),
    db:Session=Depends(get_db),
):
    target=db.get(User,target_user_id)
    if not target or target.tenant_id!=user.tenant_id:
        raise HTTPException(404,"User not found")
    allowed_roles={"Institution Admin","Teacher","Student","Parent / Guardian","Accounts","HR","Campus Admin","Auditor"}
    data=payload.model_dump(exclude_unset=True)
    if "role" in data:
        role=(data["role"] or "").strip()
        if role not in allowed_roles: raise HTTPException(400,"Unsupported role")
        if target.id==user.id and role!="Institution Admin":
            raise HTTPException(409,"You cannot remove your own Institution Admin role")
        target.role=role
    if "is_active" in data:
        if target.id==user.id and data["is_active"] is False:
            raise HTTPException(409,"You cannot deactivate your own account")
        target.is_active=data["is_active"]
    if "name" in data: target.name=data["name"].strip()
    if "campus_id" in data: target.campus_id=data["campus_id"]
    audit(db,user,"UPDATE","user",f"user_id={target.id};fields={','.join(sorted(data.keys()))}")
    db.commit(); db.refresh(target)
    return {"id":target.id,"name":target.name,"email":target.email,"role":target.role,"campus_id":target.campus_id,"is_active":target.is_active}

def _assigned_unit_ids(db:Session,user:User):
    return set(db.scalars(select(AcademicAssignment.unit_id).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==user.id,AcademicAssignment.status=="Active")).all())

def _record_unit_id(record:Record):
    if not record.code.startswith("UNIT:"): return None
    try: return int(record.code.split("|",1)[0].split(":",1)[1])
    except (ValueError,IndexError): return None

@app.get("/api/v1/my-academics")
def my_academics(user:User=Depends(require_roles("Student","Teacher")),db:Session=Depends(get_db)):
    assignments=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.user_id==user.id,AcademicAssignment.status=="Active").order_by(AcademicAssignment.id)).all()
    result=[]
    for a in assignments:
        unit=db.get(AcademicUnit,a.unit_id)
        if unit and unit.tenant_id==user.tenant_id: result.append({"assignment_id":a.id,"assignment_type":a.assignment_type,"unit_id":unit.id,"unit_type":unit.unit_type,"name":unit.name,"code":unit.code,"status":a.status})
    return result

@app.get("/api/v1/teacher-roster")
def teacher_roster(user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    assignments=db.scalars(select(AcademicAssignment).where(
        AcademicAssignment.tenant_id==user.tenant_id,
        AcademicAssignment.user_id==user.id,
        AcademicAssignment.status=="Active",
        AcademicAssignment.assignment_type.in_(["FACULTY_ASSIGNMENT","ADVISOR_ASSIGNMENT"]),
    ).order_by(AcademicAssignment.id)).all()
    classes=[]; student_map={}
    for assignment in assignments:
        unit=db.get(AcademicUnit,assignment.unit_id)
        if not unit or unit.unit_type not in {"COURSE","SECTION_BATCH"}: continue
        student_ids=sorted(_students_for_unit(db,user.tenant_id,unit.id))
        classes.append({"assignment_id":assignment.id,"assignment_type":assignment.assignment_type,"unit_id":unit.id,"unit_type":unit.unit_type,"name":unit.name,"code":unit.code,"student_count":len(student_ids)})
        for sid in student_ids:
            student=db.get(User,sid)
            if not student or student.role!="Student" or not student.is_active: continue
            item=student_map.setdefault(sid,{"student_user_id":sid,"student_name":student.name,"classes":[]})
            item["classes"].append({"unit_id":unit.id,"name":unit.name,"code":unit.code,"unit_type":unit.unit_type})
    students=sorted(student_map.values(),key=lambda x:x["student_name"].lower())
    return {"classes":classes,"students":students}

@app.get("/api/v1/academic-activities")
def academic_activities(module:str,user:User=Depends(require_roles("Student","Teacher")),db:Session=Depends(get_db)):
    if not can(user.role,module,"view"): raise HTTPException(403,"This academic module is not available for your role")
    unit_ids=_assigned_unit_ids(db,user)
    if not unit_ids: return []
    rows=db.scalars(select(Record).where(Record.tenant_id==user.tenant_id,Record.module==module).order_by(Record.id.desc())).all()
    result=[]
    for r in rows:
        unit_id=_record_unit_id(r)
        if unit_id in unit_ids:
            result.append({"id":r.id,"module":r.module,"name":r.name,"code":r.code.split("|",1)[1] if "|" in r.code else "","category":r.category,"status":r.status,"notes":r.notes,"unit_id":unit_id})
    return result

@app.post("/api/v1/academic-activities")
def create_academic_activity(payload:AcademicActivityIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    if not can(user.role,payload.module,"create"): raise HTTPException(403,"You cannot create this academic activity")
    if payload.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(403,"This course or section is not assigned to you")
    unit=db.get(AcademicUnit,payload.unit_id)
    if not unit or unit.tenant_id!=user.tenant_id: raise HTTPException(400,"Invalid academic unit")
    r=Record(tenant_id=user.tenant_id,campus_id=user.campus_id,module=payload.module,name=payload.name,code=f"UNIT:{unit.id}|{payload.code}",category=payload.category,status=payload.status,notes=payload.notes)
    db.add(r); audit(db,user,"CREATE",payload.module,f"{unit.code}:{payload.name}"); db.commit(); db.refresh(r)
    return {"id":r.id,"module":r.module,"name":r.name,"unit_id":unit.id,"unit_name":unit.name,"status":r.status}

def _parse_due_at(value):
    if not value: return None
    try: return dt.datetime.fromisoformat(value.replace("Z","+00:00")).replace(tzinfo=None)
    except ValueError: raise HTTPException(400,"Invalid due date")

def _descendant_unit_ids(db:Session,tenant_id:int,unit_id:int):
    """Return a unit and all of its descendants inside the same institution."""
    result={unit_id}; frontier=[unit_id]
    while frontier:
        children=set(db.scalars(select(AcademicUnit.id).where(
            AcademicUnit.tenant_id==tenant_id,
            AcademicUnit.parent_id.in_(frontier),
        )).all())
        children-=result
        if not children: break
        result.update(children); frontier=list(children)
    return result

def _students_for_unit(db:Session,tenant_id:int,unit_id:int):
    # A course-level activity also applies to students enrolled in child
    # sections/batches. Section-level activities remain scoped to that section.
    scoped_units=_descendant_unit_ids(db,tenant_id,unit_id)
    ids=db.scalars(select(AcademicAssignment.user_id).where(
        AcademicAssignment.tenant_id==tenant_id,
        AcademicAssignment.unit_id.in_(scoped_units),
        AcademicAssignment.status=="Active",
        AcademicAssignment.assignment_type.in_(["COURSE_REGISTRATION","SECTION_ASSIGNMENT","ENROLLMENT"]),
    )).all()
    if not ids: return set()
    students=db.scalars(select(User.id).where(
        User.tenant_id==tenant_id,
        User.id.in_(set(ids)),
        User.role=="Student",
        User.is_active==True,
    )).all()
    return set(students)

@app.get("/api/v1/parents/messages/recipients")
def parent_message_recipients(user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    links=db.scalars(select(ParentStudentLink).where(
        ParentStudentLink.parent_user_id==user.id,ParentStudentLink.tenant_id==user.tenant_id)).all()
    result=[]; seen=set()
    for link in links:
        student=db.get(User,link.student_user_id)
        if not student or student.tenant_id!=user.tenant_id or student.role!="Student" or not student.is_active: continue
        unit_ids=_assigned_unit_ids(db,student)
        for uid in unit_ids:
            assignments=db.scalars(select(AcademicAssignment).where(
                AcademicAssignment.tenant_id==user.tenant_id,
                AcademicAssignment.unit_id==uid,
                AcademicAssignment.assignment_type=="TEACHER",
                AcademicAssignment.status=="Active",
            )).all()
            for assignment in assignments:
                teacher=db.get(User,assignment.user_id)
                key=(teacher.id if teacher else None,student.id)
                if teacher and teacher.tenant_id==user.tenant_id and teacher.role=="Teacher" and teacher.is_active and key not in seen:
                    seen.add(key); result.append({"user_id":teacher.id,"name":teacher.name,"student_user_id":student.id,"student_name":student.name})
    return result

@app.get("/api/v1/parents/messages")
def parent_messages(user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CommunicationMessage).where(
        CommunicationMessage.tenant_id==user.tenant_id,
        ((CommunicationMessage.sender_user_id==user.id)|(CommunicationMessage.recipient_user_id==user.id)),
    ).order_by(CommunicationMessage.created_at.desc())).all()
    valid_child_ids={x["id"] for x in parent_children(user,db)}
    result=[]
    for row in rows:
        if row.student_user_id is not None and row.student_user_id not in valid_child_ids: continue
        sender=db.get(User,row.sender_user_id); recipient=db.get(User,row.recipient_user_id)
        student=db.get(User,row.student_user_id) if row.student_user_id else None
        result.append({"id":row.id,"direction":"Sent" if row.sender_user_id==user.id else "Received",
                       "sender":sender.name if sender and sender.tenant_id==user.tenant_id else "Unknown",
                       "recipient":recipient.name if recipient and recipient.tenant_id==user.tenant_id else "Unknown",
                       "student_name":student.name if student and student.tenant_id==user.tenant_id else None,
                       "subject":row.subject,"body":row.body,"status":row.status,"created_at":row.created_at})
    return result

@app.post("/api/v1/parents/messages")
def send_parent_message(payload:TeacherMessageIn,user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    if not payload.student_user_id: raise HTTPException(400,"Student context is required")
    student=_linked_child(db,user,payload.student_user_id)
    teacher=db.get(User,payload.recipient_user_id)
    if not teacher or teacher.tenant_id!=user.tenant_id or teacher.role!="Teacher" or not teacher.is_active:
        raise HTTPException(404,"Teacher not available")
    unit_ids=_assigned_unit_ids(db,student)
    allowed=False
    for uid in unit_ids:
        if db.scalar(select(AcademicAssignment.id).where(
            AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.unit_id==uid,
            AcademicAssignment.user_id==teacher.id,AcademicAssignment.assignment_type=="TEACHER",
            AcademicAssignment.status=="Active")):
            allowed=True; break
    if not allowed: raise HTTPException(403,"Teacher is not assigned to the selected child")
    row=CommunicationMessage(tenant_id=user.tenant_id,sender_user_id=user.id,recipient_user_id=teacher.id,
                             student_user_id=student.id,subject=payload.subject.strip(),body=payload.body.strip())
    db.add(row); audit(db,user,"MESSAGE","Communication",payload.subject.strip()); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"created_at":row.created_at}

@app.get("/api/v1/teacher/communication/recipients")
def teacher_communication_recipients(user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    unit_ids=_assigned_unit_ids(db,user)
    student_ids=set()
    for unit_id in unit_ids:
        student_ids.update(_students_for_unit(db,user.tenant_id,unit_id))
    rows=[]
    for sid in sorted(student_ids):
        student=db.get(User,sid)
        if not student or student.tenant_id!=user.tenant_id: continue
        rows.append({"user_id":student.id,"name":student.name,"role":"Student","student_user_id":student.id})
        links=db.scalars(select(ParentStudentLink).where(
            ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.student_user_id==sid
        )).all()
        for link in links:
            parent=db.get(User,link.parent_user_id)
            if parent and parent.tenant_id==user.tenant_id:
                rows.append({"user_id":parent.id,"name":parent.name,"role":"Parent / Guardian","student_user_id":sid,"student_name":student.name})
    return rows

@app.get("/api/v1/teacher/communication")
def teacher_communication(user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CommunicationMessage).where(
        CommunicationMessage.tenant_id==user.tenant_id,
        CommunicationMessage.sender_user_id==user.id,
    ).order_by(CommunicationMessage.created_at.desc())).all()
    result=[]
    for row in rows:
        recipient=db.get(User,row.recipient_user_id)
        student=db.get(User,row.student_user_id) if row.student_user_id else None
        result.append({"id":row.id,"recipient":recipient.name if recipient and recipient.tenant_id==user.tenant_id else "Unknown",
                       "recipient_role":recipient.role if recipient and recipient.tenant_id==user.tenant_id else "",
                       "student_name":student.name if student and student.tenant_id==user.tenant_id else None,
                       "subject":row.subject,"body":row.body,"status":row.status,"created_at":row.created_at})
    return result

@app.post("/api/v1/teacher/communication")
def send_teacher_communication(payload:TeacherMessageIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    recipient=db.get(User,payload.recipient_user_id)
    if not recipient or recipient.tenant_id!=user.tenant_id or recipient.role not in ("Student","Parent / Guardian"):
        raise HTTPException(404,"Recipient not available")
    unit_ids=_assigned_unit_ids(db,user)
    allowed_students=set()
    for unit_id in unit_ids: allowed_students.update(_students_for_unit(db,user.tenant_id,unit_id))
    context_student=payload.student_user_id
    if recipient.role=="Student":
        context_student=recipient.id
        if recipient.id not in allowed_students: raise HTTPException(403,"Student is not in your assigned classes")
    else:
        if not context_student or context_student not in allowed_students: raise HTTPException(403,"Guardian communication requires one of your students")
        link=db.scalar(select(ParentStudentLink.id).where(
            ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.parent_user_id==recipient.id,
            ParentStudentLink.student_user_id==context_student
        ))
        if not link: raise HTTPException(403,"Guardian is not linked to the selected student")
    row=CommunicationMessage(tenant_id=user.tenant_id,sender_user_id=user.id,recipient_user_id=recipient.id,
                             student_user_id=context_student,subject=payload.subject.strip(),body=payload.body.strip())
    db.add(row); audit(db,user,"MESSAGE","Communication",payload.subject.strip()); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"created_at":row.created_at}

@app.get("/api/v1/teacher/notes")
def teacher_notes(user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    rows=db.scalars(select(TeacherNote).where(
        TeacherNote.tenant_id==user.tenant_id,
        TeacherNote.teacher_user_id==user.id,
    ).order_by(TeacherNote.created_at.desc())).all()
    result=[]
    for row in rows:
        student=db.get(User,row.student_user_id)
        unit=db.get(AcademicUnit,row.unit_id) if row.unit_id else None
        if not student or student.tenant_id!=user.tenant_id: continue
        result.append({"id":row.id,"student_user_id":student.id,"student_name":student.name,
                       "unit_id":row.unit_id,"unit_name":unit.name if unit and unit.tenant_id==user.tenant_id else None,
                       "subject":row.subject,"note":row.note,"visibility":row.visibility,"created_at":row.created_at})
    return result

@app.post("/api/v1/teacher/notes")
def create_teacher_note(payload:TeacherNoteIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    classes=_assigned_unit_ids(db,user)
    student_units=[x for x in classes if payload.student_user_id in _students_for_unit(db,user.tenant_id,x)]
    if not student_units: raise HTTPException(403,"Student is not enrolled in one of your assigned classes")
    if payload.unit_id is not None and payload.unit_id not in student_units:
        raise HTTPException(403,"Selected class does not contain this student")
    visibility=payload.visibility.strip().upper()
    if visibility not in {"PRIVATE","STUDENT","GUARDIAN"}: raise HTTPException(400,"Invalid note visibility")
    row=TeacherNote(tenant_id=user.tenant_id,teacher_user_id=user.id,student_user_id=payload.student_user_id,
                    unit_id=payload.unit_id,subject=payload.subject.strip(),note=payload.note.strip(),visibility=visibility)
    db.add(row); audit(db,user,"CREATE","Teacher Notes",payload.subject.strip()); db.commit(); db.refresh(row)
    return {"id":row.id,"subject":row.subject,"visibility":row.visibility,"created_at":row.created_at}

@app.put("/api/v1/teacher/notes/{note_id}")
def update_teacher_note(note_id:int,payload:TeacherNoteUpdateIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    row=db.scalar(select(TeacherNote).where(TeacherNote.id==note_id,TeacherNote.tenant_id==user.tenant_id,TeacherNote.teacher_user_id==user.id))
    if not row: raise HTTPException(404,"Teacher note not found")
    classes=_assigned_unit_ids(db,user)
    if row.unit_id not in classes or row.student_user_id not in _students_for_unit(db,user.tenant_id,row.unit_id):
        raise HTTPException(403,"Student is no longer in this assigned class")
    visibility=payload.visibility.strip().upper()
    if visibility not in {"PRIVATE","STUDENT","GUARDIAN"}: raise HTTPException(400,"Invalid note visibility")
    row.subject=payload.subject.strip(); row.note=payload.note.strip(); row.visibility=visibility
    audit(db,user,"UPDATE","Teacher Notes",f"{row.id}:{row.subject}"); db.commit()
    return {"id":row.id,"visibility":row.visibility}

@app.get("/api/v1/academic-work")
def list_academic_work(work_type:Optional[str]=None,user:User=Depends(require_roles("Student","Teacher")),db:Session=Depends(get_db)):
    unit_ids=_assigned_unit_ids(db,user)
    if not unit_ids: return []
    st=select(AcademicWork).where(AcademicWork.tenant_id==user.tenant_id,AcademicWork.unit_id.in_(unit_ids))
    if user.role=="Teacher": st=st.where(AcademicWork.teacher_user_id==user.id)
    if work_type: st=st.where(AcademicWork.work_type==work_type.upper())
    if user.role=="Student": st=st.where(AcademicWork.status=="PUBLISHED")
    rows=db.scalars(st.order_by(AcademicWork.id.desc())).all()
    result=[]
    for w in rows:
        item={"id":w.id,"unit_id":w.unit_id,"work_type":w.work_type,"title":w.title,"description":w.description,"max_marks":w.max_marks,"due_at":w.due_at,"status":w.status}
        if user.role=="Student":
            sub=db.scalar(select(StudentAcademicWork).where(StudentAcademicWork.work_id==w.id,StudentAcademicWork.student_user_id==user.id))
            item["submission"]=None if not sub else {"status":sub.status,"submitted_at":sub.submitted_at,"marks":sub.marks,"grade":sub.grade,"feedback":sub.feedback}
        result.append(item)
    return result

@app.post("/api/v1/academic-work")
def create_work(payload:AcademicWorkIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    kind=payload.work_type.strip().upper()
    if kind not in {"HOMEWORK","ASSIGNMENT","EXAM"}: raise HTTPException(400,"Unsupported academic work type")
    if payload.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(403,"This course or section is not assigned to you")
    unit=db.get(AcademicUnit,payload.unit_id)
    if not unit or unit.tenant_id!=user.tenant_id: raise HTTPException(400,"Invalid academic unit")
    if unit.unit_type not in {"COURSE","SECTION_BATCH"}: raise HTTPException(400,"Academic work can only be created for a Course or Section / Batch")
    w=AcademicWork(tenant_id=user.tenant_id,unit_id=payload.unit_id,teacher_user_id=user.id,work_type=kind,title=payload.title,description=payload.description,max_marks=payload.max_marks,due_at=_parse_due_at(payload.due_at))
    db.add(w); audit(db,user,"CREATE",kind,payload.title); db.commit(); db.refresh(w)
    return {"id":w.id,"title":w.title,"work_type":w.work_type,"status":w.status}

@app.put("/api/v1/academic-work/{work_id}")
def update_academic_work(work_id:int,payload:AcademicWorkUpdateIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    w=db.scalar(select(AcademicWork).where(AcademicWork.id==work_id,AcademicWork.tenant_id==user.tenant_id,AcademicWork.teacher_user_id==user.id))
    if not w or w.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(404,"Academic work not found")
    if w.work_type not in {"HOMEWORK","ASSIGNMENT","EXAM"}: raise HTTPException(400,"Unsupported academic work type")
    status=payload.status.strip().upper()
    if status not in {"PUBLISHED","CLOSED","CANCELLED"}: raise HTTPException(400,"Invalid academic work status")
    max_marks=float(payload.max_marks)
    highest=db.scalar(select(func.max(StudentAcademicWork.marks)).where(StudentAcademicWork.work_id==w.id))
    if highest is not None and max_marks<float(highest): raise HTTPException(409,"Maximum marks cannot be lower than marks already awarded")
    due=_parse_due_at(payload.due_at)
    w.title=payload.title.strip(); w.description=payload.description.strip(); w.max_marks=max_marks; w.due_at=due; w.status=status
    audit(db,user,"UPDATE",w.work_type,f"{w.id}:{w.title}:{status}"); db.commit()
    return {"id":w.id,"status":w.status}

@app.post("/api/v1/academic-work/{work_id}/submit")
def submit_work(work_id:int,payload:SubmissionIn,user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    w=db.get(AcademicWork,work_id)
    if not w or w.tenant_id!=user.tenant_id or w.unit_id not in _assigned_unit_ids(db,user) or w.status!="PUBLISHED": raise HTTPException(404,"Academic work not found")
    if w.work_type not in {"HOMEWORK","ASSIGNMENT"}: raise HTTPException(400,"This work type does not accept student submissions")
    now=dt.datetime.utcnow()
    if w.due_at and now>w.due_at: raise HTTPException(409,"Submission deadline has passed")
    sub=db.scalar(select(StudentAcademicWork).where(StudentAcademicWork.work_id==work_id,StudentAcademicWork.student_user_id==user.id))
    if sub and sub.status=="GRADED": raise HTTPException(409,"Graded work cannot be resubmitted")
    if not sub:
        sub=StudentAcademicWork(tenant_id=user.tenant_id,work_id=work_id,student_user_id=user.id)
        db.add(sub)
    sub.submission_text=payload.submission_text.strip(); sub.submitted_at=now; sub.status="SUBMITTED"
    audit(db,user,"SUBMIT",w.work_type,w.title); db.commit(); db.refresh(sub)
    return {"id":sub.id,"status":sub.status,"submitted_at":sub.submitted_at}

@app.get("/api/v1/academic-work/{work_id}/submissions")
def work_submissions(work_id:int,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    w=db.get(AcademicWork,work_id)
    if not w or w.tenant_id!=user.tenant_id or w.teacher_user_id!=user.id or w.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(404,"Academic work not found")
    students=_students_for_unit(db,user.tenant_id,w.unit_id)
    result=[]
    for sid in students:
        student=db.get(User,sid); sub=db.scalar(select(StudentAcademicWork).where(StudentAcademicWork.work_id==work_id,StudentAcademicWork.student_user_id==sid))
        result.append({"student_id":sid,"student_name":student.name if student else "Student","submission_id":sub.id if sub else None,"status":sub.status if sub else "PENDING","marks":sub.marks if sub else None,"grade":sub.grade if sub else "","feedback":sub.feedback if sub else ""})
    return result

@app.put("/api/v1/academic-work/{work_id}/students/{student_id}/grade")
def grade_work(work_id:int,student_id:int,payload:GradeIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    w=db.get(AcademicWork,work_id)
    if not w or w.tenant_id!=user.tenant_id or w.teacher_user_id!=user.id or w.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(404,"Academic work not found")
    if student_id not in _students_for_unit(db,user.tenant_id,w.unit_id): raise HTTPException(400,"Student is not enrolled in this course or section")
    if w.max_marks and payload.marks>w.max_marks: raise HTTPException(400,"Marks cannot exceed maximum marks")
    sub=db.scalar(select(StudentAcademicWork).where(StudentAcademicWork.work_id==work_id,StudentAcademicWork.student_user_id==student_id))
    if not sub:
        sub=StudentAcademicWork(tenant_id=user.tenant_id,work_id=work_id,student_user_id=student_id)
        db.add(sub)
    sub.marks=payload.marks; sub.grade=payload.grade.strip(); sub.feedback=payload.feedback; sub.status="GRADED"
    audit(db,user,"GRADE",w.work_type,f"{w.title}:student={student_id}"); db.commit()
    return {"ok":True,"marks":sub.marks,"grade":sub.grade,"status":sub.status}

@app.get("/api/v1/class-sessions")
def class_sessions(user:User=Depends(require_roles("Student","Teacher")),db:Session=Depends(get_db)):
    unit_ids=_assigned_unit_ids(db,user)
    if not unit_ids: return []
    st=select(ClassSession).where(ClassSession.tenant_id==user.tenant_id,ClassSession.unit_id.in_(unit_ids))
    if user.role=="Teacher": st=st.where(ClassSession.teacher_user_id==user.id)
    if user.role=="Student": st=st.where(ClassSession.status!="CANCELLED")
    rows=db.scalars(st.order_by(ClassSession.starts_at.desc())).all()
    result=[]
    for x in rows:
        unit=db.get(AcademicUnit,x.unit_id)
        teacher=db.get(User,x.teacher_user_id)
        result.append({"id":x.id,"unit_id":x.unit_id,"unit_name":unit.name if unit and unit.tenant_id==user.tenant_id else None,
                       "unit_code":unit.code if unit and unit.tenant_id==user.tenant_id else None,
                       "teacher":teacher.name if teacher and teacher.tenant_id==user.tenant_id else None,
                       "title":x.title,"starts_at":x.starts_at,"ends_at":x.ends_at,"room":x.room,"status":x.status})
    return result

@app.post("/api/v1/class-sessions")
def create_class_session(payload:ClassSessionIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    if payload.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(403,"This course or section is not assigned to you")
    unit=db.get(AcademicUnit,payload.unit_id)
    if not unit or unit.tenant_id!=user.tenant_id: raise HTTPException(400,"Invalid academic unit")
    if unit.unit_type not in {"COURSE","SECTION_BATCH"}: raise HTTPException(400,"Class sessions can only be scheduled for a Course or Section / Batch")
    start=_parse_due_at(payload.starts_at); end=_parse_due_at(payload.ends_at)
    if not start or not end or end<=start: raise HTTPException(400,"Session end time must be after start time")
    overlap=select(ClassSession).where(
        ClassSession.tenant_id==user.tenant_id,
        ClassSession.status!="CANCELLED",
        ClassSession.starts_at < end,
        ClassSession.ends_at > start,
    )
    teacher_conflict=db.scalar(overlap.where(ClassSession.teacher_user_id==user.id))
    if teacher_conflict:
        raise HTTPException(409,f"Teacher already has an overlapping class session: {teacher_conflict.title}")
    unit_conflict=db.scalar(overlap.where(ClassSession.unit_id==payload.unit_id))
    if unit_conflict:
        raise HTTPException(409,f"This course or section already has an overlapping class session: {unit_conflict.title}")
    room=(payload.room or "").strip()
    if room:
        room_conflict=db.scalar(overlap.where(ClassSession.room==room))
        if room_conflict:
            raise HTTPException(409,f"Room is already booked for an overlapping class session: {room_conflict.title}")
    row=ClassSession(tenant_id=user.tenant_id,unit_id=payload.unit_id,teacher_user_id=user.id,title=payload.title,starts_at=start,ends_at=end,room=room)
    db.add(row); audit(db,user,"CREATE","class_session",payload.title); db.commit(); db.refresh(row)
    return {"id":row.id,"title":row.title,"status":row.status}

@app.put("/api/v1/class-sessions/{session_id}")
def update_class_session(session_id:int,payload:ClassSessionUpdateIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    row=db.scalar(select(ClassSession).where(ClassSession.id==session_id,ClassSession.tenant_id==user.tenant_id,ClassSession.teacher_user_id==user.id))
    if not row: raise HTTPException(404,"Class session not found")
    start=_parse_due_at(payload.starts_at); end=_parse_due_at(payload.ends_at)
    if not start or not end or end<=start: raise HTTPException(400,"Session end time must be after start time")
    status=payload.status.strip().upper()
    if status not in {"SCHEDULED","COMPLETED","CANCELLED"}: raise HTTPException(400,"Invalid session status")
    if status!="CANCELLED":
        overlap=select(ClassSession).where(ClassSession.tenant_id==user.tenant_id,ClassSession.id!=row.id,ClassSession.status!="CANCELLED",ClassSession.starts_at<end,ClassSession.ends_at>start)
        if db.scalar(overlap.where(ClassSession.teacher_user_id==user.id)): raise HTTPException(409,"You already have another class session at this time")
        if db.scalar(overlap.where(ClassSession.unit_id==row.unit_id)): raise HTTPException(409,"This course or section already has another class session at this time")
        room=(payload.room or "").strip()
        if room and db.scalar(overlap.where(ClassSession.room==room)): raise HTTPException(409,"Room is already booked for this time")
    else: room=(payload.room or "").strip()
    row.title=payload.title.strip(); row.starts_at=start; row.ends_at=end; row.room=room; row.status=status
    audit(db,user,"UPDATE","class_session",f"{row.id}:{row.title}:{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/class-sessions/{session_id}/attendance")
def session_attendance(session_id:int,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    session=db.get(ClassSession,session_id)
    if not session or session.tenant_id!=user.tenant_id or session.teacher_user_id!=user.id: raise HTTPException(404,"Class session not found")
    students=_students_for_unit(db,user.tenant_id,session.unit_id)
    result=[]
    for sid in students:
        student=db.get(User,sid)
        entry=db.scalar(select(AttendanceEntry).where(AttendanceEntry.session_id==session_id,AttendanceEntry.student_user_id==sid))
        result.append({"student_user_id":sid,"student_name":student.name if student else "Student","status":entry.status if entry else "UNMARKED","note":entry.note if entry else ""})
    return result

@app.put("/api/v1/class-sessions/{session_id}/attendance")
def mark_attendance(session_id:int,payload:AttendanceMarkIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    session=db.get(ClassSession,session_id)
    if not session or session.tenant_id!=user.tenant_id or session.teacher_user_id!=user.id: raise HTTPException(404,"Class session not found")
    if payload.student_user_id not in _students_for_unit(db,user.tenant_id,session.unit_id): raise HTTPException(400,"Student is not enrolled in this class")
    status=payload.status.strip().upper()
    if status not in {"PRESENT","ABSENT","LATE","EXCUSED"}: raise HTTPException(400,"Invalid attendance status")
    entry=db.scalar(select(AttendanceEntry).where(AttendanceEntry.session_id==session_id,AttendanceEntry.student_user_id==payload.student_user_id))
    if not entry:
        entry=AttendanceEntry(tenant_id=user.tenant_id,session_id=session_id,student_user_id=payload.student_user_id,marked_by=user.id)
        db.add(entry)
    entry.status=status; entry.note=(payload.note or "").strip(); entry.marked_by=user.id; entry.marked_at=dt.datetime.utcnow()
    audit(db,user,"ATTENDANCE",f"session:{session_id}",f"student={payload.student_user_id}:{status}"); db.commit()
    return {"ok":True,"status":status}

@app.get("/api/v1/my-attendance")
def my_attendance(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    assigned=_assigned_unit_ids(db,user)
    # Include sessions created at a parent course when the student is assigned
    # to one of that course's child sections/batches.
    visible_units=set(assigned)
    for unit_id in list(assigned):
        unit=db.get(AcademicUnit,unit_id)
        seen=set()
        while unit and unit.parent_id and unit.parent_id not in seen:
            seen.add(unit.parent_id)
            parent=db.get(AcademicUnit,unit.parent_id)
            if not parent or parent.tenant_id!=user.tenant_id: break
            if parent.unit_type=="COURSE": visible_units.add(parent.id)
            unit=parent
    if not visible_units:
        return {"percentage":None,"attended":0,"absent":0,"late":0,"excused":0,"marked_sessions":0,"counted_sessions":0,"sessions":[]}
    sessions=db.scalars(select(ClassSession).where(ClassSession.tenant_id==user.tenant_id,ClassSession.unit_id.in_(visible_units),ClassSession.status!="CANCELLED").order_by(ClassSession.starts_at.desc())).all()
    rows=[]; attended=0; absent=0; late=0; excused=0; marked=0; counted=0
    for session in sessions:
        if user.id not in _students_for_unit(db,user.tenant_id,session.unit_id): continue
        entry=db.scalar(select(AttendanceEntry).where(AttendanceEntry.session_id==session.id,AttendanceEntry.student_user_id==user.id))
        status=entry.status if entry else "UNMARKED"
        if status!="UNMARKED":
            marked+=1
            if status=="EXCUSED":
                excused+=1
            else:
                counted+=1
                if status=="PRESENT": attended+=1
                elif status=="LATE": attended+=1; late+=1
                elif status=="ABSENT": absent+=1
        unit=db.get(AcademicUnit,session.unit_id); teacher=db.get(User,session.teacher_user_id)
        rows.append({"session_id":session.id,"unit_name":unit.name if unit and unit.tenant_id==user.tenant_id else None,"unit_code":unit.code if unit and unit.tenant_id==user.tenant_id else None,"teacher":teacher.name if teacher and teacher.tenant_id==user.tenant_id else None,"title":session.title,"starts_at":session.starts_at,"room":session.room,"status":status})
    return {"percentage":round(attended*100/counted,1) if counted else None,"attended":attended,"absent":absent,"late":late,"excused":excused,"marked_sessions":marked,"counted_sessions":counted,"sessions":rows}

@app.get("/api/v1/grade-rules")
def grade_rules(user:User=Depends(current_user),db:Session=Depends(get_db)):
    rows=db.scalars(select(GradeRule).where(GradeRule.tenant_id==user.tenant_id).order_by(GradeRule.min_percentage.desc())).all()
    return [{"id":r.id,"name":r.name,"min_percentage":r.min_percentage,"max_percentage":r.max_percentage,"grade":r.grade,"grade_point":r.grade_point,"result_status":r.result_status} for r in rows]

@app.post("/api/v1/grade-rules")
def create_grade_rule(payload:GradeRuleIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    if payload.max_percentage<payload.min_percentage: raise HTTPException(400,"Maximum percentage must be greater than or equal to minimum percentage")
    if payload.grade_point is not None and payload.grade_point<0: raise HTTPException(400,"Grade point cannot be negative")
    result_status=payload.result_status.strip().upper()
    if result_status not in {"PASS","FAIL"}: raise HTTPException(400,"Result status must be PASS or FAIL")
    if not payload.name.strip() or not payload.grade.strip(): raise HTTPException(400,"Grade rule name and grade are required")
    overlap=db.scalar(select(GradeRule).where(GradeRule.tenant_id==user.tenant_id,GradeRule.min_percentage<=payload.max_percentage,GradeRule.max_percentage>=payload.min_percentage))
    if overlap: raise HTTPException(409,"Grade percentage range overlaps an existing rule")
    data=payload.model_dump(); data["name"]=payload.name.strip(); data["grade"]=payload.grade.strip().upper(); data["result_status"]=result_status
    r=GradeRule(tenant_id=user.tenant_id,**data)
    db.add(r); audit(db,user,"CREATE","grade_rule",f"{r.grade}:{r.min_percentage}-{r.max_percentage}"); db.commit(); db.refresh(r)
    return {"id":r.id,"grade":r.grade}

@app.delete("/api/v1/grade-rules/{rule_id}")
def delete_grade_rule(rule_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    r=db.get(GradeRule,rule_id)
    if not r or r.tenant_id!=user.tenant_id: raise HTTPException(404,"Grade rule not found")
    db.delete(r); audit(db,user,"DELETE","grade_rule",r.grade); db.commit(); return {"ok":True}

def _grading_scheme_gaps(db:Session,tenant_id:int):
    rules=db.scalars(select(GradeRule).where(GradeRule.tenant_id==tenant_id).order_by(GradeRule.min_percentage,GradeRule.max_percentage)).all()
    if not rules: return [(0.0,100.0)]
    gaps=[]; cursor=0.0
    for rule in rules:
        if rule.min_percentage>cursor: gaps.append((cursor,rule.min_percentage))
        cursor=max(cursor,rule.max_percentage)
    if cursor<100.0: gaps.append((cursor,100.0))
    return gaps

def _grade_for(db:Session,tenant_id:int,percentage:float):
    return db.scalar(select(GradeRule).where(GradeRule.tenant_id==tenant_id,GradeRule.min_percentage<=percentage,GradeRule.max_percentage>=percentage).order_by(GradeRule.min_percentage.desc()))

@app.get("/api/v1/exams/{work_id}/results")
def exam_results_register(work_id:int,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    exam=db.get(AcademicWork,work_id)
    if not exam or exam.tenant_id!=user.tenant_id or exam.work_type!="EXAM" or exam.teacher_user_id!=user.id or exam.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(404,"Exam not found")
    student_ids=sorted(_students_for_unit(db,user.tenant_id,exam.unit_id))
    saved={r.student_user_id:r for r in db.scalars(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id,ExamResult.work_id==work_id)).all()}
    rows=[]
    for sid in student_ids:
        student=db.get(User,sid); r=saved.get(sid)
        rows.append({"student_id":sid,"student_name":student.name if student else "Student","marks":r.marks if r else None,"percentage":r.percentage if r else None,"grade":r.grade if r else "","grade_point":r.grade_point if r else None,"result_status":r.result_status if r else "","remarks":r.remarks if r else "","published":bool(r.published) if r else False})
    return {"exam":{"id":exam.id,"title":exam.title,"max_marks":exam.max_marks,"unit_id":exam.unit_id},"students":rows,"complete":bool(student_ids) and all(sid in saved for sid in student_ids),"published":bool(saved) and all(r.published for r in saved.values())}

@app.put("/api/v1/exams/{work_id}/results")
def save_exam_result(work_id:int,payload:ExamResultIn,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    exam=db.get(AcademicWork,work_id)
    if not exam or exam.tenant_id!=user.tenant_id or exam.work_type!="EXAM" or exam.teacher_user_id!=user.id or exam.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(404,"Exam not found")
    if payload.student_user_id not in _students_for_unit(db,user.tenant_id,exam.unit_id): raise HTTPException(400,"Student is not enrolled in this exam course")
    if exam.max_marks<=0: raise HTTPException(400,"Exam maximum marks must be greater than zero")
    if payload.marks>exam.max_marks: raise HTTPException(400,"Marks cannot exceed maximum marks")
    percentage=round(payload.marks*100/exam.max_marks,2); rule=_grade_for(db,user.tenant_id,percentage)
    if not rule: raise HTTPException(409,"No grading rule covers this percentage")
    row=db.scalar(select(ExamResult).where(ExamResult.work_id==work_id,ExamResult.student_user_id==payload.student_user_id))
    if row and row.published: raise HTTPException(409,"Published results are locked and cannot be edited")
    if not row:
        row=ExamResult(tenant_id=user.tenant_id,work_id=work_id,student_user_id=payload.student_user_id,marks=payload.marks,percentage=percentage,grade=rule.grade,grade_point=rule.grade_point,result_status=rule.result_status,remarks=payload.remarks)
        db.add(row)
    else:
        row.marks=payload.marks; row.percentage=percentage; row.grade=rule.grade; row.grade_point=rule.grade_point; row.result_status=rule.result_status; row.remarks=payload.remarks
    audit(db,user,"GRADE","exam_result",f"exam={work_id}:student={payload.student_user_id}:{rule.grade}"); db.commit()
    return {"ok":True,"percentage":percentage,"grade":rule.grade,"grade_point":rule.grade_point,"result_status":rule.result_status}

@app.post("/api/v1/exams/{work_id}/publish")
def publish_exam_results(work_id:int,user:User=Depends(require_roles("Teacher")),db:Session=Depends(get_db)):
    exam=db.get(AcademicWork,work_id)
    if not exam or exam.tenant_id!=user.tenant_id or exam.work_type!="EXAM" or exam.teacher_user_id!=user.id or exam.unit_id not in _assigned_unit_ids(db,user): raise HTTPException(404,"Exam not found")
    gaps=_grading_scheme_gaps(db,user.tenant_id)
    if gaps:
        formatted=", ".join(f"{a:g}-{b:g}%" for a,b in gaps)
        raise HTTPException(409,f"Grading scheme is incomplete. Configure coverage for: {formatted}")
    student_ids=_students_for_unit(db,user.tenant_id,exam.unit_id)
    if not student_ids: raise HTTPException(409,"No enrolled students for this exam")
    rows=db.scalars(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id,ExamResult.work_id==work_id)).all()
    entered={r.student_user_id for r in rows}
    missing=student_ids-entered
    if missing: raise HTTPException(409,f"Enter results for all enrolled students before publishing. Missing: {len(missing)}")
    for r in rows: r.published=True
    audit(db,user,"PUBLISH","exam_results",f"exam={work_id}:count={len(rows)}"); db.commit(); return {"ok":True,"published":len(rows)}

@app.get("/api/v1/my-results")
def my_results(user:User=Depends(require_roles("Student")),db:Session=Depends(get_db)):
    rows=db.scalars(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id,ExamResult.student_user_id==user.id,ExamResult.published==True).order_by(ExamResult.id.desc())).all()
    result=[]; points=[]
    for r in rows:
        exam=db.get(AcademicWork,r.work_id); unit=db.get(AcademicUnit,exam.unit_id) if exam else None
        if exam and unit and exam.tenant_id==user.tenant_id and unit.tenant_id==user.tenant_id and exam.work_type=="EXAM":
            result.append({"exam_id":exam.id,"exam":exam.title,"course":unit.name,"marks":r.marks,"max_marks":exam.max_marks,"percentage":r.percentage,"grade":r.grade,"grade_point":r.grade_point,"result_status":r.result_status,"remarks":r.remarks})
            if r.grade_point is not None: points.append(r.grade_point)
    average=round(sum(points)/len(points),2) if points else None
    return {"results":result,"average_grade_point":average,"gpa":average}

@app.get("/api/v1/records")
def records(
    module: Optional[str]=None,
    q: Optional[str]=None,
    user: User=Depends(current_user),
    db: Session=Depends(get_db),
):
    st = select(Record).where(Record.tenant_id==user.tenant_id)
    if user.role=="Campus Admin":
        st = st.where(Record.campus_id==user.campus_id)
    if module:
        if not can(user.role, module, "view"):
            raise HTTPException(403, "This module is not available for your role")
        st=st.where(Record.module==module)
    elif user.role not in {"Institution Admin", "Campus Admin", "Auditor"}:
        raise HTTPException(400, "module is required for this role")
    if q:
        st=st.where(Record.name.ilike(f"%{q}%"))
    rows=db.scalars(st.order_by(Record.id.desc())).all()
    return [
        {"id":r.id,"module":r.module,"name":r.name,"code":r.code,"category":r.category,
         "status":r.status,"notes":r.notes,"created_at":r.created_at}
        for r in rows
    ]

@app.post("/api/v1/records")
def create_record(
    payload: RecordIn,
    user: User=Depends(current_user),
    db: Session=Depends(get_db),
):
    if not can(user.role, payload.module, "create"):
        raise HTTPException(403, "You do not have permission to create records in this module")
    r=Record(
        tenant_id=user.tenant_id,campus_id=user.campus_id,
        **payload.model_dump()
    )
    db.add(r)
    audit(db,user,"CREATE",payload.module,payload.name)
    db.commit(); db.refresh(r)
    return {"id":r.id,**payload.model_dump()}

@app.put("/api/v1/records/{rid}")
def update_record(
    rid:int,payload:RecordIn,
    user:User=Depends(current_user),
    db:Session=Depends(get_db),
):
    if not can(user.role, payload.module, "update"):
        raise HTTPException(403, "You do not have permission to update records in this module")
    r=db.get(Record,rid)
    if not r or r.tenant_id!=user.tenant_id:
        raise HTTPException(404,"Record not found")
    if user.role=="Campus Admin" and r.campus_id!=user.campus_id:
        raise HTTPException(403,"Outside campus scope")
    for k,v in payload.model_dump().items():
        setattr(r,k,v)
    audit(db,user,"UPDATE",f"{payload.module}:{rid}",payload.name)
    db.commit()
    return {"ok":True}

@app.delete("/api/v1/records/{rid}")
def delete_record(
    rid:int,
    user:User=Depends(current_user),
    db:Session=Depends(get_db),
):
    r=db.get(Record,rid)
    if not r or r.tenant_id!=user.tenant_id:
        raise HTTPException(404,"Record not found")
    if not can(user.role, r.module, "delete"):
        raise HTTPException(403, "You do not have permission to delete records in this module")
    if user.role=="Campus Admin" and r.campus_id!=user.campus_id:
        raise HTTPException(403,"Outside campus scope")
    audit(db,user,"DELETE",f"{r.module}:{r.id}",r.name)
    db.delete(r); db.commit()
    return {"ok":True}

@app.get("/api/v1/admin/parent-student-links")
def admin_parent_student_links(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    links=db.scalars(select(ParentStudentLink).where(ParentStudentLink.tenant_id==user.tenant_id).order_by(ParentStudentLink.id)).all()
    result=[]
    for link in links:
        parent=db.get(User,link.parent_user_id); student=db.get(User,link.student_user_id)
        if parent and student:
            result.append({"id":link.id,"parent_user_id":parent.id,"parent_name":parent.name,"parent_email":parent.email,"student_user_id":student.id,"student_name":student.name,"student_email":student.email,"relationship":link.relationship})
    return result

@app.post("/api/v1/admin/parent-student-links")
def create_parent_student_link(payload:ParentStudentLinkIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    parent=db.get(User,payload.parent_user_id); student=db.get(User,payload.student_user_id)
    if not parent or parent.tenant_id!=user.tenant_id or parent.role!="Parent / Guardian" or not parent.is_active:
        raise HTTPException(400,"Invalid parent or guardian")
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student" or not student.is_active:
        raise HTTPException(400,"Invalid student")
    existing=db.scalar(select(ParentStudentLink).where(ParentStudentLink.parent_user_id==parent.id,ParentStudentLink.student_user_id==student.id))
    if existing: raise HTTPException(409,"This parent and student are already linked")
    row=ParentStudentLink(parent_user_id=parent.id,student_user_id=student.id,relationship=payload.relationship.strip(),tenant_id=user.tenant_id)
    db.add(row); db.flush(); audit(db,user,"CREATE","parent_student_link",f"parent={parent.id};student={student.id};relationship={row.relationship}"); db.commit(); db.refresh(row)
    return {"id":row.id,"parent_user_id":parent.id,"student_user_id":student.id,"relationship":row.relationship}

@app.delete("/api/v1/admin/parent-student-links/{link_id}")
def delete_parent_student_link(link_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(ParentStudentLink,link_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Parent-student link not found")
    details=f"parent={row.parent_user_id};student={row.student_user_id};relationship={row.relationship}"
    db.delete(row); audit(db,user,"DELETE","parent_student_link",details); db.commit()
    return {"ok":True}

@app.get("/api/v1/parents/children")
def parent_children(
    user:User=Depends(require_roles("Parent / Guardian")),
    db:Session=Depends(get_db),
):
    links=db.scalars(select(ParentStudentLink).where(
        ParentStudentLink.parent_user_id==user.id,
        ParentStudentLink.tenant_id==user.tenant_id,
    )).all()
    result=[]
    for link in links:
        student=db.get(User,link.student_user_id)
        if student and student.tenant_id==user.tenant_id and student.role=="Student" and student.is_active:
            result.append({
                "id":student.id,"name":student.name,"email":student.email,
                "relationship":link.relationship,
            })
    return result

def _fee_payload(row:FeeLedger):
    balance=max(0,row.amount_due-row.amount_paid)
    status="CANCELLED" if row.status=="CANCELLED" else ("PAID" if balance<=0 else ("PARTIAL" if row.amount_paid>0 else "DUE"))
    return {"id":row.id,"student_user_id":row.student_user_id,"fee_code":row.fee_code,"title":row.title,"amount_due":float(row.amount_due),"amount_paid":float(row.amount_paid),"balance":float(balance),"due_at":row.due_at,"status":status}

@app.get("/api/v1/finance/students")
def finance_students(user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Student",User.is_active==True).order_by(User.name)).all()
    return [{"id":x.id,"name":x.name,"email":x.email} for x in rows]

@app.get("/api/v1/finance/concessions")
def finance_concessions(user:User=Depends(require_roles("Accounts","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(FeeConcession).where(FeeConcession.tenant_id==user.tenant_id).order_by(FeeConcession.created_at.desc())).all()
    result=[]
    for row in rows:
        ledger=db.get(FeeLedger,row.ledger_id); student=db.get(User,row.student_user_id)
        result.append({"id":row.id,"ledger_id":row.ledger_id,"student_user_id":row.student_user_id,
                       "student_name":student.name if student else f"Student {row.student_user_id}",
                       "fee_code":ledger.fee_code if ledger else "","fee_title":ledger.title if ledger else "",
                       "amount":float(row.amount),"reason":row.reason,"status":row.status,"created_at":row.created_at})
    return result

@app.post("/api/v1/finance/concessions")
def create_finance_concession(payload:FeeConcessionIn,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    ledger=db.get(FeeLedger,payload.ledger_id)
    if not ledger or ledger.tenant_id!=user.tenant_id: raise HTTPException(404,"Fee ledger entry not found")
    if ledger.status=="CANCELLED": raise HTTPException(409,"Cancelled fees cannot receive concessions")
    amount=Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if amount<=0: raise HTTPException(400,"Concession amount must be greater than zero")
    balance=max(Decimal("0.00"),ledger.amount_due-ledger.amount_paid)
    if amount>balance: raise HTTPException(400,"Concession cannot exceed outstanding balance")
    row=FeeConcession(tenant_id=user.tenant_id,ledger_id=ledger.id,student_user_id=ledger.student_user_id,
                      amount=amount,reason=payload.reason.strip(),status="APPROVED",approved_by=user.id)
    ledger.amount_due-=amount
    ledger.status="PAID" if ledger.amount_paid>=ledger.amount_due else ("PARTIAL" if ledger.amount_paid>0 else "DUE")
    db.add(row); audit(db,user,"CONCESSION","fee_ledger",f"ledger={ledger.id};amount={amount}"); db.commit(); db.refresh(row)
    return {"id":row.id,"ledger_id":row.ledger_id,"amount":float(row.amount),"status":row.status}

@app.get("/api/v1/finance/refunds")
def finance_refunds(user:User=Depends(require_roles("Accounts","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(FeeRefund).where(FeeRefund.tenant_id==user.tenant_id).order_by(FeeRefund.created_at.desc())).all()
    result=[]
    for row in rows:
        student=db.get(User,row.student_user_id); ledger=db.get(FeeLedger,row.ledger_id)
        result.append({"id":row.id,"payment_id":row.payment_id,"student_user_id":row.student_user_id,
                       "student_name":student.name if student else f"Student {row.student_user_id}",
                       "fee_code":ledger.fee_code if ledger else "","fee_title":ledger.title if ledger else "",
                       "amount":float(row.amount),"reason":row.reason,"reference":row.reference,
                       "status":row.status,"created_at":row.created_at})
    return result

@app.post("/api/v1/finance/refunds")
def create_finance_refund(payload:FeeRefundIn,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    payment=db.get(FeePayment,payload.payment_id)
    if not payment or payment.tenant_id!=user.tenant_id: raise HTTPException(404,"Payment not found")
    ledger=db.get(FeeLedger,payment.ledger_id)
    if not ledger or ledger.tenant_id!=user.tenant_id: raise HTTPException(404,"Fee ledger entry not found")
    refunded=db.scalar(select(func.coalesce(func.sum(FeeRefund.amount),0)).where(FeeRefund.tenant_id==user.tenant_id,FeeRefund.payment_id==payment.id))
    amount=Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if amount<=0: raise HTTPException(400,"Refund amount must be greater than zero")
    available=Decimal(str(payment.amount))-Decimal(str(refunded or 0))
    if amount>available: raise HTTPException(400,"Refund cannot exceed the unrefunded payment amount")
    if amount>ledger.amount_paid: raise HTTPException(400,"Refund cannot exceed the ledger paid amount")
    reference=payload.reference.strip()
    if reference and db.scalar(select(FeeRefund).where(FeeRefund.tenant_id==user.tenant_id,FeeRefund.reference==reference)): raise HTTPException(409,"This refund reference has already been recorded")
    row=FeeRefund(tenant_id=user.tenant_id,payment_id=payment.id,ledger_id=ledger.id,student_user_id=payment.student_user_id,
                  amount=amount,reason=payload.reason.strip(),reference=reference,status="COMPLETED",recorded_by=user.id)
    ledger.amount_paid-=amount
    ledger.status="PAID" if ledger.amount_paid>=ledger.amount_due else ("PARTIAL" if ledger.amount_paid>0 else "DUE")
    db.add(row); audit(db,user,"REFUND","fee_ledger",f"ledger={ledger.id};payment={payment.id};amount={amount}"); db.commit(); db.refresh(row)
    return {"id":row.id,"amount":float(row.amount),"status":row.status}

@app.get("/api/v1/finance/reconciliations")
def finance_reconciliations(user:User=Depends(require_roles("Accounts","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(FinanceReconciliation).where(FinanceReconciliation.tenant_id==user.tenant_id).order_by(FinanceReconciliation.reconciliation_date.desc())).all()
    return [{"id":x.id,"reconciliation_date":x.reconciliation_date,"expected_amount":float(x.expected_amount),"bank_amount":float(x.bank_amount),"difference":float(x.difference),"reference":x.reference,"notes":x.notes,"status":x.status,"created_at":x.created_at} for x in rows]

@app.post("/api/v1/finance/reconciliations")
def create_finance_reconciliation(payload:FinanceReconciliationIn,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    try: day=dt.datetime.fromisoformat(payload.reconciliation_date)
    except ValueError: raise HTTPException(400,"Invalid reconciliation date")
    start=day.replace(hour=0,minute=0,second=0,microsecond=0); end=start+dt.timedelta(days=1)
    payments=db.scalar(select(func.coalesce(func.sum(FeePayment.amount),0)).where(FeePayment.tenant_id==user.tenant_id,FeePayment.paid_at>=start,FeePayment.paid_at<end))
    refunds=db.scalar(select(func.coalesce(func.sum(FeeRefund.amount),0)).where(FeeRefund.tenant_id==user.tenant_id,FeeRefund.created_at>=start,FeeRefund.created_at<end))
    expected=Decimal(str(payments or 0))-Decimal(str(refunds or 0)); bank=Decimal(str(payload.bank_amount)).quantize(Decimal("0.01")); difference=bank-expected
    reference=payload.reference.strip()
    if reference and db.scalar(select(FinanceReconciliation).where(FinanceReconciliation.tenant_id==user.tenant_id,FinanceReconciliation.reference==reference)): raise HTTPException(409,"This reconciliation reference has already been recorded")
    row=FinanceReconciliation(tenant_id=user.tenant_id,reconciliation_date=start,expected_amount=expected,bank_amount=bank,difference=difference,reference=reference,notes=payload.notes.strip(),status="MATCHED" if difference==0 else "VARIANCE",recorded_by=user.id)
    db.add(row); audit(db,user,"RECONCILE","finance",f"date={start.date()};expected={expected};bank={bank};difference={difference}"); db.commit(); db.refresh(row)
    return {"id":row.id,"expected_amount":float(row.expected_amount),"bank_amount":float(row.bank_amount),"difference":float(row.difference),"status":row.status}

@app.get("/api/v1/finance/payments")
def finance_payments(user:User=Depends(require_roles("Accounts","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(FeePayment).where(FeePayment.tenant_id==user.tenant_id).order_by(FeePayment.paid_at.desc())).all()
    result=[]
    for x in rows:
        ledger=db.get(FeeLedger,x.ledger_id); student=db.get(User,x.student_user_id)
        result.append({"id":x.id,"ledger_id":x.ledger_id,"fee_code":ledger.fee_code if ledger else "","fee_title":ledger.title if ledger else "","student_user_id":x.student_user_id,"student_name":student.name if student else f"Student {x.student_user_id}","amount":float(x.amount),"reference":x.reference,"receipt_no":x.receipt_no,"paid_at":x.paid_at})
    return result

@app.get("/api/v1/fee-ledger")
def fee_ledger(user:User=Depends(current_user),db:Session=Depends(get_db)):
    st=select(FeeLedger).where(FeeLedger.tenant_id==user.tenant_id)
    if user.role=="Student": st=st.where(FeeLedger.student_user_id==user.id)
    elif user.role not in {"Accounts","Institution Admin","Auditor"}: raise HTTPException(403,"Fee ledger is not available for your role")
    return [_fee_payload(x) for x in db.scalars(st.order_by(FeeLedger.id.desc())).all()]

@app.post("/api/v1/fee-ledger")
def create_fee_ledger(payload:FeeLedgerIn,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    student=db.get(User,payload.student_user_id)
    if not student or student.tenant_id!=user.tenant_id or student.role!="Student" or not student.is_active: raise HTTPException(400,"Invalid student")
    code=payload.fee_code.strip().upper()
    if db.scalar(select(FeeLedger).where(FeeLedger.tenant_id==user.tenant_id,FeeLedger.student_user_id==student.id,FeeLedger.fee_code==code)): raise HTTPException(409,"This fee is already assigned to the student")
    due=_parse_due_at(payload.due_at)
    row=FeeLedger(tenant_id=user.tenant_id,student_user_id=student.id,fee_code=code,title=payload.title.strip(),amount_due=payload.amount_due,amount_paid=0,due_at=due,status="DUE")
    db.add(row); db.flush(); audit(db,user,"CREATE","fee_ledger",f"student={student.id};fee={code};amount={payload.amount_due}"); db.commit(); db.refresh(row)
    return _fee_payload(row)

@app.patch("/api/v1/fee-ledger/{ledger_id}")
def update_fee_ledger(ledger_id:int,payload:FeeLedgerUpdateIn,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(FeeLedger,ledger_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Fee ledger entry not found")
    if row.status=="CANCELLED": raise HTTPException(409,"Cancelled fee assignments cannot be edited")
    amount=Decimal(str(payload.amount_due)).quantize(Decimal("0.01"))
    if amount<row.amount_paid: raise HTTPException(409,"Assigned amount cannot be lower than payments already collected")
    due=_parse_due_at(payload.due_at)
    row.title=payload.title.strip(); row.amount_due=amount; row.due_at=due
    row.status="PAID" if row.amount_paid>=row.amount_due else ("PARTIAL" if row.amount_paid>0 else "DUE")
    audit(db,user,"UPDATE","fee_ledger",f"ledger={row.id};amount={amount};status={row.status}"); db.commit(); db.refresh(row)
    return _fee_payload(row)

@app.post("/api/v1/fee-ledger/{ledger_id}/cancel")
def cancel_fee_ledger(ledger_id:int,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(FeeLedger,ledger_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Fee ledger entry not found")
    if row.amount_paid>0: raise HTTPException(409,"A fee with recorded payments cannot be cancelled")
    if row.status=="CANCELLED": return _fee_payload(row)
    row.status="CANCELLED"; audit(db,user,"CANCEL","fee_ledger",f"ledger={row.id};student={row.student_user_id}"); db.commit()
    return _fee_payload(row)

@app.get("/api/v1/finance/report")
def finance_report(start_date:str|None=None,end_date:str|None=None,user:User=Depends(require_roles("Accounts","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    st=select(FeePayment).where(FeePayment.tenant_id==user.tenant_id)
    try:
        start=dt.datetime.fromisoformat(start_date) if start_date else None
        end=dt.datetime.fromisoformat(end_date) if end_date else None
        if start and end and start>end: raise HTTPException(400,"Report start date cannot be after end date")
        if start: st=st.where(FeePayment.paid_at>=start)
        if end:
            if len(end_date)<=10: end=end+dt.timedelta(days=1)
            st=st.where(FeePayment.paid_at<end)
    except ValueError: raise HTTPException(400,"Invalid report date")
    rows=db.scalars(st.order_by(FeePayment.paid_at.desc())).all()
    items=[]; total=0
    for x in rows:
        ledger=db.get(FeeLedger,x.ledger_id); student=db.get(User,x.student_user_id); total+=x.amount
        items.append({"receipt_no":x.receipt_no,"student_id":x.student_user_id,"student_name":student.name if student else f"Student {x.student_user_id}","student_email":student.email if student else "","fee_code":ledger.fee_code if ledger else "","fee_title":ledger.title if ledger else "","amount":x.amount,"reference":x.reference,"paid_at":x.paid_at})
    return {"start_date":start_date,"end_date":end_date,"payment_count":len(items),"total_collected":float(total),"payments":items}

@app.get("/api/v1/finance/summary")
def finance_summary(user:User=Depends(require_roles("Accounts","Institution Admin","Auditor")),db:Session=Depends(get_db)):
    rows=db.scalars(select(FeeLedger).where(FeeLedger.tenant_id==user.tenant_id)).all()
    active=[x for x in rows if x.status!="CANCELLED"]
    assigned=sum((x.amount_due for x in active),0); collected=sum((x.amount_paid for x in active),0); outstanding=max(0,assigned-collected)
    return {"assigned":float(assigned),"collected":float(collected),"outstanding":float(outstanding),"ledger_count":len(active),"paid_count":sum(1 for x in active if x.amount_paid>=x.amount_due),"partial_count":sum(1 for x in active if 0<x.amount_paid<x.amount_due),"due_count":sum(1 for x in active if x.amount_paid<=0)}

@app.post("/api/v1/fee-ledger/{ledger_id}/payments")
def record_fee_payment(ledger_id:int,payload:FeePaymentIn,user:User=Depends(require_roles("Accounts","Institution Admin")),db:Session=Depends(get_db)):
    row=db.get(FeeLedger,ledger_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Fee ledger entry not found")
    if row.status=="CANCELLED": raise HTTPException(409,"Cancelled fees cannot receive payments")
    balance=max(0,row.amount_due-row.amount_paid)
    reference=payload.reference.strip()
    if reference and db.scalar(select(FeePayment).where(FeePayment.tenant_id==user.tenant_id,FeePayment.reference==reference)): raise HTTPException(409,"This payment reference has already been recorded")
    payment_amount=Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if payment_amount<=0: raise HTTPException(400,"Payment amount must be greater than zero")
    if balance<=0: raise HTTPException(409,"This fee has no outstanding balance")
    if payment_amount>balance: raise HTTPException(400,"Payment cannot exceed outstanding balance")
    receipt=f"GAINT-{user.tenant_id}-{dt.datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}-{ledger_id}"
    payment=FeePayment(tenant_id=user.tenant_id,ledger_id=row.id,student_user_id=row.student_user_id,amount=payment_amount,reference=reference,receipt_no=receipt,recorded_by=user.id)
    row.amount_paid+=payment_amount; row.status="PAID" if row.amount_paid>=row.amount_due else "PARTIAL"
    db.add(payment); audit(db,user,"PAYMENT","fee_ledger",f"student={row.student_user_id};receipt={receipt};amount={payment_amount}"); db.commit()
    return {"ok":True,"receipt_no":receipt,"ledger":_fee_payload(row)}

@app.get("/api/v1/fee-ledger/{ledger_id}/receipts")
def fee_receipts(ledger_id:int,user:User=Depends(current_user),db:Session=Depends(get_db)):
    row=db.get(FeeLedger,ledger_id)
    if not row or row.tenant_id!=user.tenant_id: raise HTTPException(404,"Fee ledger entry not found")
    allowed=user.role in {"Accounts","Institution Admin","Auditor"} or (user.role=="Student" and row.student_user_id==user.id)
    if user.role=="Parent / Guardian":
        try:
            _linked_child(db,user,row.student_user_id)
            allowed=True
        except HTTPException:
            allowed=False
    if not allowed: raise HTTPException(403,"You cannot view these receipts")
    rows=db.scalars(select(FeePayment).where(FeePayment.ledger_id==ledger_id,FeePayment.tenant_id==user.tenant_id).order_by(FeePayment.paid_at.desc())).all()
    return [{"id":x.id,"amount":x.amount,"reference":x.reference,"receipt_no":x.receipt_no,"paid_at":x.paid_at} for x in rows]

@app.get("/api/v1/parents/dashboard")
def parent_dashboard(user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    children=parent_children(user,db)
    result=[]
    total_balance=0.0
    for child in children:
        student_id=child["id"]
        fee_rows=db.scalars(select(FeeLedger).where(
            FeeLedger.tenant_id==user.tenant_id,FeeLedger.student_user_id==student_id,
            FeeLedger.status!="CANCELLED",
        )).all()
        balance=sum(float(max(0,x.amount_due-x.amount_paid)) for x in fee_rows)
        total_balance+=balance
        student=_linked_child(db,user,student_id)
        unit_ids=_assigned_unit_ids(db,student)
        sessions=db.scalars(select(ClassSession).where(
            ClassSession.tenant_id==user.tenant_id,
            ClassSession.unit_id.in_(unit_ids) if unit_ids else False,
            ClassSession.status!="CANCELLED",
        )).all() if unit_ids else []
        marked=present=0
        for session in sessions:
            if student.id not in _students_for_unit(db,user.tenant_id,session.unit_id): continue
            entry=db.scalar(select(AttendanceEntry).where(
                AttendanceEntry.tenant_id==user.tenant_id,
                AttendanceEntry.session_id==session.id,
                AttendanceEntry.student_user_id==student_id))
            if entry and entry.status not in {"UNMARKED","EXCUSED"}:
                marked+=1
                if entry.status in ("PRESENT","LATE"): present+=1
        result.append({**child,"fee_balance":balance,"attendance_percentage":round(present*100/marked,1) if marked else None})
    return {"children":result,"linked_children":len(result),"total_fee_balance":round(total_balance,2)}

@app.get("/api/v1/parents/children/{student_id}/transport")
def parent_child_transport(student_id:int,user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    student=_linked_child(db,user,student_id)
    allocation=db.scalar(select(StudentTransportAllocation).where(
        StudentTransportAllocation.tenant_id==user.tenant_id,
        StudentTransportAllocation.student_user_id==student.id,
        StudentTransportAllocation.status=="Active",
    ))
    if not allocation: return {"student":{"id":student.id,"name":student.name},"allocated":False}
    route=db.get(TransportRoute,allocation.route_id)
    vehicle=db.get(TransportVehicle,allocation.vehicle_id) if allocation.vehicle_id else None
    stop=db.get(TransportStop,allocation.stop_id) if allocation.stop_id else None
    return {"student":{"id":student.id,"name":student.name},"allocated":True,
            "route":{"id":route.id,"name":route.name,"code":route.code} if route and route.tenant_id==user.tenant_id else None,
            "vehicle":{"id":vehicle.id,"vehicle_number":vehicle.vehicle_number,"label":vehicle.label} if vehicle and vehicle.tenant_id==user.tenant_id else None,
            "stop":{"id":stop.id,"name":stop.name,"pickup_time":stop.pickup_time,"drop_time":stop.drop_time} if stop and stop.tenant_id==user.tenant_id else None,
            "status":allocation.status}

@app.get("/api/v1/parents/children/{student_id}/fees")
def parent_child_fees(student_id:int,user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    student=_linked_child(db,user,student_id)
    rows=db.scalars(select(FeeLedger).where(FeeLedger.tenant_id==user.tenant_id,FeeLedger.student_user_id==student.id).order_by(FeeLedger.id.desc())).all()
    return {"student":{"id":student.id,"name":student.name,"email":student.email},"records":[_fee_payload(x) for x in rows],"payment_ready":False,"message":"Fee ledger is live. Online gateway payment remains disabled until a production payment provider is configured."}

def _linked_child(db:Session,parent:User,student_id:int):
    link=db.scalar(select(ParentStudentLink).where(
        ParentStudentLink.parent_user_id==parent.id,
        ParentStudentLink.student_user_id==student_id,
        ParentStudentLink.tenant_id==parent.tenant_id,
    ))
    if not link: raise HTTPException(403,"This student is not linked to your account")
    student=db.get(User,student_id)
    if not student or student.tenant_id!=parent.tenant_id or student.role!="Student" or not student.is_active:
        raise HTTPException(404,"Linked student not found")
    return student

@app.get("/api/v1/parents/children/{student_id}/academics")
def parent_child_academics(student_id:int,user:User=Depends(require_roles("Parent / Guardian")),db:Session=Depends(get_db)):
    student=_linked_child(db,user,student_id)
    unit_ids=_assigned_unit_ids(db,student)
    visible_units=set(unit_ids)
    for uid in list(unit_ids):
        unit=db.get(AcademicUnit,uid)
        while unit and unit.parent_id:
            unit=db.get(AcademicUnit,unit.parent_id)
            if not unit or unit.tenant_id!=user.tenant_id: break
            if unit.unit_type=="COURSE": visible_units.add(unit.id)
    works=db.scalars(select(AcademicWork).where(
        AcademicWork.tenant_id==user.tenant_id,
        AcademicWork.unit_id.in_(visible_units) if visible_units else False,
    ).order_by(AcademicWork.id.desc())).all() if visible_units else []
    homework=[]
    for work in works:
        if student.id not in _students_for_unit(db,user.tenant_id,work.unit_id): continue
        if work.work_type not in {"HOMEWORK","ASSIGNMENT"} or work.status!="PUBLISHED": continue
        submission=db.scalar(select(StudentAcademicWork).where(StudentAcademicWork.work_id==work.id,StudentAcademicWork.student_user_id==student.id))
        homework.append({"id":work.id,"work_type":work.work_type,"title":work.title,"due_at":work.due_at,"status":submission.status if submission else "NOT_SUBMITTED","score":submission.score if submission else None})

    sessions=db.scalars(select(ClassSession).where(
        ClassSession.tenant_id==user.tenant_id,
        ClassSession.unit_id.in_(visible_units) if visible_units else False,
    ).order_by(ClassSession.starts_at.desc())).all() if visible_units else []
    attendance=[]; attended=0; counted=0; excused=0
    for session in sessions:
        if student.id not in _students_for_unit(db,user.tenant_id,session.unit_id) or session.status=="CANCELLED": continue
        entry=db.scalar(select(AttendanceEntry).where(AttendanceEntry.session_id==session.id,AttendanceEntry.student_user_id==student.id))
        status=entry.status if entry else "UNMARKED"
        if status=="EXCUSED": excused+=1
        elif status!="UNMARKED":
            counted+=1
            if status in {"PRESENT","LATE"}: attended+=1
        attendance.append({"session_id":session.id,"title":session.title,"starts_at":session.starts_at,"room":session.room,"status":status})

    results=db.scalars(select(ExamResult).where(
        ExamResult.tenant_id==user.tenant_id,
        ExamResult.student_user_id==student.id,
        ExamResult.published==True,
    ).order_by(ExamResult.id.desc())).all()
    result_rows=[]
    for result in results:
        exam=db.get(AcademicWork,result.work_id)
        if exam and exam.tenant_id==user.tenant_id and exam.work_type=="EXAM": result_rows.append({"exam_id":exam.id,"title":exam.title,"marks":result.marks,"percentage":result.percentage,"grade":result.grade,"grade_point":result.grade_point,"result_status":result.result_status})

    audit(db,user,"ACADEMIC_VIEW",f"student:{student.id}","parent_link_verified"); db.commit()
    return {"student":{"id":student.id,"name":student.name,"email":student.email},"attendance":{"percentage":round(attended*100/counted,1) if counted else None,"attended":attended,"counted_sessions":counted,"excused":excused,"sessions":attendance},"homework":homework,"results":result_rows}

def _latest_location(db:Session, student_id:int, tenant_id:int):
    return db.scalar(
        select(StudentLocation)
        .where(
            StudentLocation.student_user_id==student_id,
            StudentLocation.tenant_id==tenant_id,
        )
        .order_by(desc(StudentLocation.recorded_at),desc(StudentLocation.id))
        .limit(1)
    )

@app.post("/api/v1/location/update")
def update_location(
    payload:LocationUpdate,
    user:User=Depends(require_roles("Student")),
    db:Session=Depends(get_db),
):
    allowed_contexts={"TRANSPORT","SCHOOL_HOURS","FIELD_TRIP","SOS"}
    context=payload.tracking_context.strip().upper()
    if context not in allowed_contexts:
        raise HTTPException(400,"Tracking context is not allowed")
    source=payload.source.strip().upper()
    if source not in {"MOBILE","GPS"}: raise HTTPException(400,"Location source is not allowed")
    status=payload.status.strip().upper()
    if status not in {"ACTIVE","SOS"}: raise HTTPException(400,"Location status is not allowed")
    data=payload.model_dump(); data.update({"tracking_context":context,"source":source,"status":status})
    row=StudentLocation(
        student_user_id=user.id,
        tenant_id=user.tenant_id,
        campus_id=user.campus_id,
        **data,
    )
    db.add(row)
    audit(db,user,"LOCATION_UPDATE","student_location",context)
    db.commit(); db.refresh(row)
    return {
        "id":row.id,"recorded_at":row.recorded_at,"status":row.status,
        "tracking_context":row.tracking_context
    }

@app.get("/api/v1/location/me")
def my_location(
    user:User=Depends(require_roles("Student")),
    db:Session=Depends(get_db),
):
    row=_latest_location(db,user.id,user.tenant_id)
    if not row:
        return {"available":False}
    return {
        "available":True,"student_id":user.id,"name":user.name,
        "latitude":row.latitude,"longitude":row.longitude,"accuracy":row.accuracy,
        "source":row.source,"tracking_context":row.tracking_context,"status":row.status,
        "recorded_at":row.recorded_at,
    }

@app.get("/api/v1/parents/children/{student_id}/location")
def parent_child_location(
    student_id:int,
    user:User=Depends(require_roles("Parent / Guardian")),
    db:Session=Depends(get_db),
):
    student=_linked_child(db,user,student_id)
    row=_latest_location(db,student.id,user.tenant_id)
    audit(db,user,"LOCATION_VIEW",f"student:{student.id}","parent_link_verified")
    db.commit()
    if not row:
        return {"available":False,"student_id":student.id,"name":student.name}
    return {
        "available":True,"student_id":student.id,"name":student.name,
        "latitude":row.latitude,"longitude":row.longitude,"accuracy":row.accuracy,
        "source":row.source,"tracking_context":row.tracking_context,"status":row.status,
        "recorded_at":row.recorded_at,
    }

@app.get("/api/v1/campus/live-locations")
def campus_live_locations(user:User=Depends(require_roles("Campus Admin")),db:Session=Depends(get_db)):
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.campus_id==user.campus_id,User.role=="Student")).all()
    result=[]
    for student in students:
        row=_latest_location(db,student.id,user.tenant_id)
        if row and row.campus_id==user.campus_id:
            result.append({"student_id":student.id,"name":student.name,"latitude":row.latitude,"longitude":row.longitude,"accuracy":row.accuracy,"source":row.source,"status":row.status,"tracking_context":row.tracking_context,"recorded_at":row.recorded_at})
    audit(db,user,"LOCATION_MONITOR_VIEW","campus_live_locations",f"campus={user.campus_id};count={len(result)}")
    db.commit()
    return result

@app.get("/api/v1/admin/live-locations")
def live_locations(
    user:User=Depends(require_roles("Institution Admin","Campus Admin")),
    db:Session=Depends(get_db),
):
    students=db.scalars(select(User).where(
        User.tenant_id==user.tenant_id,
        User.role=="Student",
    )).all()
    result=[]
    for student in students:
        if user.role=="Campus Admin" and student.campus_id!=user.campus_id:
            continue
        row=_latest_location(db,student.id,user.tenant_id)
        if row:
            result.append({
                "student_id":student.id,"name":student.name,
                "latitude":row.latitude,"longitude":row.longitude,
                "status":row.status,"tracking_context":row.tracking_context,
                "recorded_at":row.recorded_at,
            })
    audit(db,user,"LOCATION_MONITOR_VIEW","live_locations",f"count={len(result)}")
    db.commit()
    return result

@app.post("/api/v1/sos")
def create_sos(
    payload:SosIn,
    user:User=Depends(require_roles("Student")),
    db:Session=Depends(get_db),
):
    event=SosEvent(
        student_user_id=user.id,tenant_id=user.tenant_id,
        latitude=payload.latitude,longitude=payload.longitude,
        message=payload.message,status="OPEN",
    )
    db.add(event)
    db.add(StudentLocation(
        student_user_id=user.id,tenant_id=user.tenant_id,campus_id=user.campus_id,
        latitude=payload.latitude,longitude=payload.longitude,accuracy=0,
        source="SOS",tracking_context="SOS",status="EMERGENCY",
    ))
    audit(db,user,"SOS_CREATE","sos",payload.message)
    db.commit(); db.refresh(event)
    return {"id":event.id,"status":event.status}

@app.get("/api/v1/admin/dashboard")
def admin_dashboard(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    users=db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()
    students=[x for x in users if x.role=="Student"]; teachers=[x for x in users if x.role=="Teacher"]
    units=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id)).all()
    fees=db.scalars(select(FeeLedger).where(FeeLedger.tenant_id==user.tenant_id)).all()
    payments=db.scalars(select(FeePayment).where(FeePayment.tenant_id==user.tenant_id)).all()
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id)).all()
    visitors=db.scalars(select(CampusVisitor).where(CampusVisitor.tenant_id==user.tenant_id)).all()
    hostels=db.scalars(select(Hostel).where(Hostel.tenant_id==user.tenant_id)).all()
    allocations=db.scalars(select(HostelAllocation).where(HostelAllocation.tenant_id==user.tenant_id,HostelAllocation.status=="ACTIVE")).all()
    inventory=db.scalars(select(CampusInventoryItem).where(CampusInventoryItem.tenant_id==user.tenant_id)).all()
    assets=db.scalars(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id)).all()
    return {"summary":{"students":len(students),"active_students":sum(x.is_active for x in students),"teachers":len(teachers),"active_teachers":sum(x.is_active for x in teachers),"academic_units":len(units),"fee_assigned":round(sum(float(x.amount or 0) for x in fees),2),"fee_collected":round(sum(float(x.amount or 0) for x in payments),2),"open_grievances":sum(x.status in {"Open","In Progress"} for x in grievances),"visitors_inside":sum(x.status=="CHECKED_IN" for x in visitors),"hostels":len(hostels),"hostel_occupancy":len(allocations),"low_stock":sum(x.quantity<=x.minimum_quantity for x in inventory),"assets_attention":sum(x.condition in {"DAMAGED","REPAIR"} for x in assets)}}

@app.get("/api/v1/admin/health")
def admin_health(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    records=db.scalars(select(HealthRecord).where(HealthRecord.tenant_id==user.tenant_id).order_by(HealthRecord.updated_at.desc())).all()
    visits=db.scalars(select(HealthVisit).where(HealthVisit.tenant_id==user.tenant_id).order_by(HealthVisit.visited_at.desc()).limit(500)).all()
    ids={x.person_user_id for x in records}|{x.person_user_id for x in visits}
    people=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.id.in_(ids))).all() if ids else []
    names={x.id:x for x in people}
    return {"summary":{"health_profiles":len(records),"visits":len(visits),"emergency_contacts":sum(bool(x.emergency_contact_phone) for x in records),"referred":sum(x.disposition=="REFERRED" for x in visits),"sent_home":sum(x.disposition=="SENT_HOME" for x in visits)},"people":[{"id":x.id,"name":x.name,"email":x.email,"role":x.role,"campus_id":x.campus_id} for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role.in_(["Student","Teacher"]))).all()],"records":[{"id":x.id,"person_user_id":x.person_user_id,"person_name":names[x.person_user_id].name if x.person_user_id in names else f"User #{x.person_user_id}","person_role":names[x.person_user_id].role if x.person_user_id in names else "Unknown","campus_id":x.campus_id,"blood_group":x.blood_group,"allergies":x.allergies,"medical_conditions":x.medical_conditions,"emergency_contact_name":x.emergency_contact_name,"emergency_contact_phone":x.emergency_contact_phone,"notes":x.notes,"updated_at":x.updated_at} for x in records],"visits":[{"id":x.id,"person_user_id":x.person_user_id,"person_name":names[x.person_user_id].name if x.person_user_id in names else f"User #{x.person_user_id}","person_role":names[x.person_user_id].role if x.person_user_id in names else "Unknown","campus_id":x.campus_id,"visit_type":x.visit_type,"complaint":x.complaint,"action_taken":x.action_taken,"disposition":x.disposition,"visited_at":x.visited_at} for x in visits]}

@app.post("/api/v1/admin/health/records")
def admin_health_record(payload:HealthRecordIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    person=db.scalar(select(User).where(User.id==payload.person_user_id,User.tenant_id==user.tenant_id,User.role.in_(["Student","Teacher"])))
    if not person: raise HTTPException(404,"Student or teacher not found")
    row=db.scalar(select(HealthRecord).where(HealthRecord.tenant_id==user.tenant_id,HealthRecord.person_user_id==person.id))
    values=payload.model_dump(exclude={"person_user_id"})
    blood_group=(values.get("blood_group") or "").strip().upper().replace(" ","")
    if blood_group and blood_group not in {"A+","A-","B+","B-","AB+","AB-","O+","O-"}: raise HTTPException(400,"Invalid blood group")
    values["blood_group"]=blood_group
    if row:
        for k,v in values.items(): setattr(row,k,v.strip() if isinstance(v,str) else v)
        row.updated_at=dt.datetime.utcnow(); action="UPDATE"
    else:
        row=HealthRecord(tenant_id=user.tenant_id,campus_id=person.campus_id,person_user_id=person.id,recorded_by=user.id,**values); db.add(row); action="CREATE"
    audit(db,user,f"HEALTH_{action}",f"health_record:{person.id}",person.name); db.commit(); db.refresh(row)
    return {"id":row.id}

@app.post("/api/v1/admin/health/visits")
def admin_health_visit(payload:HealthVisitIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    person=db.scalar(select(User).where(User.id==payload.person_user_id,User.tenant_id==user.tenant_id,User.role.in_(["Student","Teacher"])))
    if not person: raise HTTPException(404,"Student or teacher not found")
    disposition=payload.disposition.strip().upper()
    if disposition not in {"RETURNED","SENT_HOME","REFERRED"}: raise HTTPException(400,"Invalid health visit disposition")
    row=HealthVisit(tenant_id=user.tenant_id,campus_id=person.campus_id,person_user_id=person.id,visit_type=payload.visit_type.strip().upper(),complaint=payload.complaint.strip(),action_taken=payload.action_taken.strip(),disposition=disposition,recorded_by=user.id)
    db.add(row); audit(db,user,"HEALTH_VISIT","health_visit",f"{person.name};{disposition}"); db.commit(); db.refresh(row)
    return {"id":row.id,"disposition":row.disposition}

@app.get("/api/v1/admin/visitors")
def admin_visitors(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CampusVisitor).where(CampusVisitor.tenant_id==user.tenant_id).order_by(CampusVisitor.id.desc()).limit(1000)).all()
    return {"summary":{"visitors":len(rows),"checked_in":sum(x.status=="CHECKED_IN" for x in rows),"checked_out":sum(x.status=="CHECKED_OUT" for x in rows),"campuses":len({x.campus_id for x in rows})},"visitors":[{"id":x.id,"campus_id":x.campus_id,"name":x.name,"phone":x.phone,"purpose":x.purpose,"person_to_meet":x.person_to_meet,"status":x.status,"checked_in_at":x.checked_in_at,"checked_out_at":x.checked_out_at} for x in rows]}

@app.post("/api/v1/admin/visitors")
def admin_visitor_checkin(payload:CampusVisitorIn,campus_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    if campus_id<1: raise HTTPException(400,"Invalid campus")
    campus_exists=db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==campus_id).limit(1))
    if not campus_exists: raise HTTPException(404,"Campus not found in this institution")
    row=CampusVisitor(tenant_id=user.tenant_id,campus_id=campus_id,recorded_by=user.id,**payload.model_dump())
    db.add(row); audit(db,user,"VISITOR_CHECK_IN","institution_visitor",f"{payload.name};campus={campus_id}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.put("/api/v1/admin/visitors/{visitor_id}")
def admin_visitor_update(visitor_id:int,payload:CampusVisitorIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusVisitor).where(CampusVisitor.id==visitor_id,CampusVisitor.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Visitor not found")
    if row.status!="CHECKED_IN": raise HTTPException(409,"Checked-out visitor records are locked")
    row.name=payload.name.strip(); row.phone=payload.phone.strip(); row.purpose=payload.purpose.strip(); row.person_to_meet=payload.person_to_meet.strip()
    audit(db,user,"VISITOR_UPDATE",f"institution_visitor:{row.id}",row.name); db.commit()
    return {"id":row.id,"status":row.status}

@app.patch("/api/v1/admin/visitors/{visitor_id}")
def admin_visitor_checkout(visitor_id:int,payload:CampusVisitorStatusIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusVisitor).where(CampusVisitor.id==visitor_id,CampusVisitor.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Visitor not found")
    if payload.status!="CHECKED_OUT": raise HTTPException(400,"Only CHECKED_OUT is allowed")
    if row.status=="CHECKED_OUT": return {"id":row.id,"status":row.status}
    row.status="CHECKED_OUT"; row.checked_out_at=dt.datetime.utcnow()
    audit(db,user,"VISITOR_CHECK_OUT",f"institution_visitor:{row.id}",row.name); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/inventory-assets")
def admin_inventory_assets(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    inventory=db.scalars(select(CampusInventoryItem).where(CampusInventoryItem.tenant_id==user.tenant_id).order_by(CampusInventoryItem.name)).all()
    assets=db.scalars(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id).order_by(CampusAsset.name)).all()
    campuses=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.unit_type=="CAMPUS",AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    return {"campuses":[{"id":x.id,"name":x.name,"code":x.code} for x in campuses],"summary":{"inventory_items":len(inventory),"total_quantity":sum(x.quantity for x in inventory),"low_stock":sum(x.quantity<=x.minimum_quantity for x in inventory),"assets":len(assets),"active_assets":sum(x.status=="ACTIVE" for x in assets),"attention_assets":sum(x.condition in {"DAMAGED","REPAIR"} for x in assets)},"inventory":[{"id":x.id,"campus_id":x.campus_id,"name":x.name,"category":x.category,"item_code":x.item_code,"quantity":x.quantity,"minimum_quantity":x.minimum_quantity,"location":x.location,"status":x.status,"notes":x.notes,"low_stock":x.quantity<=x.minimum_quantity} for x in inventory],"assets":[{"id":x.id,"campus_id":x.campus_id,"asset_code":x.asset_code,"name":x.name,"category":x.category,"serial_number":x.serial_number,"location":x.location,"assigned_to":x.assigned_to,"condition":x.condition,"status":x.status,"notes":x.notes} for x in assets]}

@app.post("/api/v1/admin/inventory")
def admin_inventory_create(payload:AdminInventoryIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    if not db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==payload.campus_id).limit(1)): raise HTTPException(404,"Campus not found in this institution")
    if payload.status not in {"ACTIVE","INACTIVE"}: raise HTTPException(400,"Invalid inventory status")
    item_code=payload.item_code.strip()
    if item_code and db.scalar(select(CampusInventoryItem.id).where(CampusInventoryItem.tenant_id==user.tenant_id,CampusInventoryItem.campus_id==payload.campus_id,CampusInventoryItem.item_code==item_code)): raise HTTPException(409,"Inventory item code already exists in this campus")
    data=payload.model_dump(); campus_id=data.pop("campus_id"); data["item_code"]=item_code
    row=CampusInventoryItem(tenant_id=user.tenant_id,campus_id=campus_id,recorded_by=user.id,**data)
    db.add(row); audit(db,user,"INVENTORY_CREATE_ADMIN","campus_inventory",payload.name); db.commit(); db.refresh(row)
    return {"id":row.id}

@app.patch("/api/v1/admin/inventory/{item_id}")
def admin_inventory_update(item_id:int,payload:CampusInventoryUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusInventoryItem).where(CampusInventoryItem.id==item_id,CampusInventoryItem.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Inventory item not found")
    if payload.status not in {"ACTIVE","INACTIVE"}: raise HTTPException(400,"Invalid inventory status")
    row.quantity=payload.quantity; row.status=payload.status; row.notes=payload.notes; row.updated_at=dt.datetime.utcnow()
    audit(db,user,"INVENTORY_UPDATE",f"inventory:{row.id}",f"quantity={row.quantity};status={row.status}"); db.commit()
    return {"id":row.id,"quantity":row.quantity,"status":row.status}

@app.post("/api/v1/admin/assets")
def admin_asset_create(payload:AdminAssetIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    if not db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==payload.campus_id).limit(1)): raise HTTPException(404,"Campus not found in this institution")
    if payload.condition not in {"GOOD","FAIR","DAMAGED","REPAIR"}: raise HTTPException(400,"Invalid asset condition")
    if payload.status not in {"ACTIVE","INACTIVE","RETIRED"}: raise HTTPException(400,"Invalid asset status")
    if db.scalar(select(CampusAsset.id).where(CampusAsset.tenant_id==user.tenant_id,CampusAsset.campus_id==payload.campus_id,CampusAsset.asset_code==payload.asset_code)): raise HTTPException(409,"Asset code already exists in this campus")
    data=payload.model_dump(); campus_id=data.pop("campus_id")
    row=CampusAsset(tenant_id=user.tenant_id,campus_id=campus_id,recorded_by=user.id,**data)
    db.add(row); audit(db,user,"ASSET_CREATE_ADMIN","campus_asset",payload.asset_code); db.commit(); db.refresh(row)
    return {"id":row.id}

@app.patch("/api/v1/admin/assets/{asset_id}")
def admin_asset_update(asset_id:int,payload:CampusAssetUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusAsset).where(CampusAsset.id==asset_id,CampusAsset.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Asset not found")
    if payload.condition not in {"GOOD","FAIR","DAMAGED","REPAIR"}: raise HTTPException(400,"Invalid asset condition")
    if payload.status not in {"ACTIVE","INACTIVE","RETIRED"}: raise HTTPException(400,"Invalid asset status")
    row.location=payload.location; row.assigned_to=payload.assigned_to; row.condition=payload.condition; row.status=payload.status; row.notes=payload.notes; row.updated_at=dt.datetime.utcnow()
    audit(db,user,"ASSET_UPDATE",f"asset:{row.id}",f"condition={row.condition};status={row.status}"); db.commit()
    return {"id":row.id,"condition":row.condition,"status":row.status}

@app.delete("/api/v1/admin/inventory/{item_id}")
def admin_inventory_delete(item_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusInventoryItem).where(CampusInventoryItem.id==item_id,CampusInventoryItem.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Inventory item not found")
    audit(db,user,"INVENTORY_DELETE_ADMIN","campus_inventory",f"{row.id}:{row.name}"); db.delete(row); db.commit(); return {"ok":True}

@app.delete("/api/v1/admin/assets/{asset_id}")
def admin_asset_delete(asset_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CampusAsset).where(CampusAsset.id==asset_id,CampusAsset.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Asset not found")
    audit(db,user,"ASSET_DELETE_ADMIN","campus_asset",f"{row.id}:{row.asset_code}"); db.delete(row); db.commit(); return {"ok":True}

@app.get("/api/v1/admin/hostels")
def admin_hostels(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    hostels=db.scalars(select(Hostel).where(Hostel.tenant_id==user.tenant_id).order_by(Hostel.name)).all()
    rooms=db.scalars(select(HostelRoom).where(HostelRoom.tenant_id==user.tenant_id).order_by(HostelRoom.room_number)).all()
    allocations=db.scalars(select(HostelAllocation).where(HostelAllocation.tenant_id==user.tenant_id).order_by(HostelAllocation.id.desc())).all()
    active=[x for x in allocations if x.status=="ACTIVE" and x.check_out_at is None]
    students={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Student")).all()}
    hostel_map={x.id:x for x in hostels}; room_map={x.id:x for x in rooms}
    campuses=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.unit_type=="CAMPUS",AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    return {"campuses":[{"id":x.id,"name":x.name,"code":x.code} for x in campuses],"summary":{"hostels":len(hostels),"rooms":len(rooms),"capacity":sum(x.capacity for x in rooms),"occupied":len(active),"available_beds":max(0,sum(x.capacity for x in rooms)-len(active))},"hostels":[{"id":x.id,"campus_id":x.campus_id,"name":x.name,"code":x.code,"hostel_type":x.hostel_type,"warden_name":x.warden_name,"warden_phone":x.warden_phone,"status":x.status} for x in hostels],"rooms":[{"id":x.id,"campus_id":x.campus_id,"hostel_id":x.hostel_id,"room_number":x.room_number,"floor":x.floor,"capacity":x.capacity,"room_type":x.room_type,"status":x.status,"occupied":sum(a.room_id==x.id for a in active)} for x in rooms],"students":[{"id":x.id,"name":x.name,"email":x.email,"campus_id":x.campus_id} for x in students.values()],"allocations":[{"id":x.id,"student_user_id":x.student_user_id,"student_name":students[x.student_user_id].name if x.student_user_id in students else f"Student #{x.student_user_id}","hostel_name":hostel_map[x.hostel_id].name if x.hostel_id in hostel_map else f"Hostel #{x.hostel_id}","room_number":room_map[x.room_id].room_number if x.room_id in room_map else f"Room #{x.room_id}","bed_number":x.bed_number,"check_in_at":x.check_in_at,"check_out_at":x.check_out_at,"status":x.status,"notes":x.notes} for x in allocations]}

@app.post("/api/v1/admin/hostels")
def admin_hostel_create(payload:HostelIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    campus_exists=db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==payload.campus_id).limit(1))
    if not campus_exists: raise HTTPException(404,"Campus not found in this institution")
    duplicate=db.scalar(select(Hostel.id).where(Hostel.tenant_id==user.tenant_id,Hostel.campus_id==payload.campus_id,Hostel.code==payload.code.strip()))
    if duplicate: raise HTTPException(409,"Hostel code already exists for this campus")
    row=Hostel(tenant_id=user.tenant_id,campus_id=payload.campus_id,name=payload.name.strip(),code=payload.code.strip(),hostel_type=payload.hostel_type.strip().upper(),warden_name=payload.warden_name.strip(),warden_phone=payload.warden_phone.strip())
    db.add(row); audit(db,user,"CREATE","Hostel",row.name); db.commit(); db.refresh(row)
    return {"id":row.id,"name":row.name,"status":row.status}

@app.patch("/api/v1/admin/hostels/{hostel_id}")
def admin_hostel_update(hostel_id:int,payload:HostelUpdateIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(Hostel).where(Hostel.id==hostel_id,Hostel.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Hostel not found")
    duplicate=db.scalar(select(Hostel.id).where(Hostel.tenant_id==user.tenant_id,Hostel.campus_id==row.campus_id,Hostel.code==payload.code.strip(),Hostel.id!=row.id))
    if duplicate: raise HTTPException(409,"Hostel code already exists for this campus")
    status=payload.status.strip().upper()
    if status not in {"ACTIVE","INACTIVE"}: raise HTTPException(400,"Invalid hostel status")
    if status=="INACTIVE" and db.scalar(select(HostelAllocation.id).where(HostelAllocation.tenant_id==user.tenant_id,HostelAllocation.hostel_id==row.id,HostelAllocation.status=="ACTIVE")): raise HTTPException(409,"Hostel with active student allocations cannot be made inactive")
    row.name=payload.name.strip(); row.code=payload.code.strip(); row.hostel_type=payload.hostel_type.strip().upper(); row.warden_name=payload.warden_name.strip(); row.warden_phone=payload.warden_phone.strip(); row.status=status
    audit(db,user,"UPDATE","Hostel",f"{row.id}:{row.name}:{status}"); db.commit()
    return {"id":row.id,"name":row.name,"status":row.status}

@app.post("/api/v1/admin/hostel-rooms")
def admin_hostel_room_create(payload:HostelRoomIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    hostel=db.scalar(select(Hostel).where(Hostel.id==payload.hostel_id,Hostel.tenant_id==user.tenant_id))
    if not hostel: raise HTTPException(404,"Hostel not found")
    duplicate=db.scalar(select(HostelRoom.id).where(HostelRoom.tenant_id==user.tenant_id,HostelRoom.hostel_id==hostel.id,HostelRoom.room_number==payload.room_number.strip()))
    if duplicate: raise HTTPException(409,"Room number already exists in this hostel")
    row=HostelRoom(tenant_id=user.tenant_id,campus_id=hostel.campus_id,hostel_id=hostel.id,room_number=payload.room_number.strip(),floor=payload.floor.strip(),capacity=payload.capacity,room_type=payload.room_type.strip().upper())
    db.add(row); audit(db,user,"CREATE","Hostel Room",f"{hostel.name}:{row.room_number}"); db.commit(); db.refresh(row)
    return {"id":row.id,"room_number":row.room_number,"status":row.status}

@app.patch("/api/v1/admin/hostel-rooms/{room_id}")
def admin_hostel_room_update(room_id:int,payload:HostelRoomUpdateIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(HostelRoom).where(HostelRoom.id==room_id,HostelRoom.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Hostel room not found")
    active=db.scalars(select(HostelAllocation).where(HostelAllocation.tenant_id==user.tenant_id,HostelAllocation.room_id==row.id,HostelAllocation.status=="ACTIVE")).all()
    if payload.capacity<len(active): raise HTTPException(409,"Room capacity cannot be lower than current occupancy")
    status=payload.status.strip().upper()
    if status not in {"AVAILABLE","INACTIVE","MAINTENANCE"}: raise HTTPException(400,"Invalid room status")
    if active and status!="AVAILABLE": raise HTTPException(409,"Occupied room must remain available until students check out")
    row.floor=payload.floor.strip(); row.capacity=payload.capacity; row.room_type=payload.room_type.strip().upper(); row.status=status
    audit(db,user,"UPDATE","Hostel Room",f"{row.id}:{row.room_number}:{status}"); db.commit()
    return {"id":row.id,"status":row.status,"capacity":row.capacity}

@app.post("/api/v1/admin/hostel-allocations")
def admin_hostel_allocate(payload:HostelAllocationIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    hostel=db.scalar(select(Hostel).where(Hostel.id==payload.hostel_id,Hostel.tenant_id==user.tenant_id))
    room=db.scalar(select(HostelRoom).where(HostelRoom.id==payload.room_id,HostelRoom.tenant_id==user.tenant_id,HostelRoom.hostel_id==payload.hostel_id))
    student=db.scalar(select(User).where(User.id==payload.student_user_id,User.tenant_id==user.tenant_id,User.role=="Student"))
    if not hostel or not room: raise HTTPException(404,"Hostel room not found")
    if not student: raise HTTPException(404,"Student not found")
    if hostel.status!="ACTIVE": raise HTTPException(409,"Hostel is not active")
    if room.status!="AVAILABLE": raise HTTPException(409,"Room is not available")
    if student.campus_id!=hostel.campus_id: raise HTTPException(409,"Student and hostel must belong to the same campus")
    existing=db.scalar(select(HostelAllocation).where(HostelAllocation.tenant_id==user.tenant_id,HostelAllocation.student_user_id==student.id,HostelAllocation.status=="ACTIVE"))
    if existing: raise HTTPException(409,"Student already has an active hostel allocation")
    occupied=db.scalars(select(HostelAllocation).where(HostelAllocation.tenant_id==user.tenant_id,HostelAllocation.room_id==room.id,HostelAllocation.status=="ACTIVE")).all()
    if len(occupied)>=room.capacity: raise HTTPException(409,"Room is at full capacity")
    if payload.bed_number and any(x.bed_number==payload.bed_number for x in occupied): raise HTTPException(409,"Bed is already allocated")
    row=HostelAllocation(tenant_id=user.tenant_id,campus_id=hostel.campus_id,hostel_id=hostel.id,room_id=room.id,student_user_id=student.id,bed_number=payload.bed_number.strip(),notes=payload.notes.strip(),allocated_by=user.id)
    db.add(row); audit(db,user,"ALLOCATE","Hostel",f"student={student.id};room={room.room_number}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.patch("/api/v1/admin/hostel-allocations/{allocation_id}/checkout")
def admin_hostel_checkout(allocation_id:int,payload:HostelCheckoutIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(HostelAllocation).where(HostelAllocation.id==allocation_id,HostelAllocation.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Hostel allocation not found")
    if row.status!="ACTIVE": raise HTTPException(409,"Allocation is not active")
    row.status="CHECKED_OUT"; row.check_out_at=dt.datetime.utcnow()
    if payload.notes.strip(): row.notes=(row.notes+"\n"+payload.notes.strip()).strip()
    audit(db,user,"CHECKOUT","Hostel",f"allocation={row.id};student={row.student_user_id}"); db.commit()
    return {"id":row.id,"status":row.status,"check_out_at":row.check_out_at}

@app.get("/api/v1/admin/library")
def admin_library(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    books=db.scalars(select(LibraryBook).where(LibraryBook.tenant_id==user.tenant_id).order_by(LibraryBook.title)).all()
    loans=db.scalars(select(LibraryLoan).where(LibraryLoan.tenant_id==user.tenant_id).order_by(LibraryLoan.issued_at.desc())).all()
    book_map={x.id:x for x in books}; borrower_ids={x.borrower_user_id for x in loans}
    borrowers=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.id.in_(borrower_ids))).all() if borrower_ids else []
    borrower_map={x.id:x for x in borrowers}; now=dt.datetime.utcnow()
    eligible=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.is_active==True,User.role.in_(["Student","Teacher"])).order_by(User.name)).all()
    campuses=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.unit_type=="CAMPUS",AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    return {"campuses":[{"id":x.id,"name":x.name,"code":x.code} for x in campuses],"summary":{"books":len(books),"available":sum(x.status=="Available" for x in books),"loans":len(loans),"active_loans":sum(x.returned_at is None for x in loans),"overdue":sum(x.returned_at is None and x.due_at<now for x in loans),"fines":round(sum(float(x.fine_amount or 0) for x in loans),2)},"books":[{"id":x.id,"campus_id":x.campus_id,"accession_no":x.accession_no,"isbn":x.isbn,"title":x.title,"author":x.author,"category":x.category,"resource_type":x.resource_type,"publisher":x.publisher,"edition":x.edition,"publication_year":x.publication_year,"language":x.language,"shelf_location":x.shelf_location,"academic_unit_id":x.academic_unit_id,"academic_unit_name":unit_map[x.academic_unit_id].name if x.academic_unit_id in unit_map else "","status":x.status} for x in books],"loans":[{"id":x.id,"campus_id":x.campus_id,"book_title":book_map[x.book_id].title if x.book_id in book_map else f"Book #{x.book_id}","borrower_name":borrower_map[x.borrower_user_id].name if x.borrower_user_id in borrower_map else f"User #{x.borrower_user_id}","borrower_role":borrower_map[x.borrower_user_id].role if x.borrower_user_id in borrower_map else "Unknown","issued_at":x.issued_at,"due_at":x.due_at,"returned_at":x.returned_at,"fine_amount":float(x.fine_amount or 0),"status":x.status,"overdue":x.returned_at is None and x.due_at<now} for x in loans],"borrowers":[{"id":x.id,"name":x.name,"role":x.role,"campus_id":x.campus_id} for x in eligible]}

@app.post("/api/v1/admin/library/books")
def admin_library_book_create(payload:AdminLibraryBookIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    campus_exists=db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==payload.campus_id).limit(1))
    if not campus_exists: raise HTTPException(404,"Campus not found in this institution")
    accession=payload.accession_no.strip()
    if db.scalar(select(LibraryBook.id).where(LibraryBook.tenant_id==user.tenant_id,LibraryBook.accession_no==accession)): raise HTTPException(409,"Accession number already exists")
    unit=db.get(AcademicUnit,payload.academic_unit_id) if payload.academic_unit_id else None
    if unit and unit.tenant_id!=user.tenant_id: raise HTTPException(400,"Academic unit does not belong to this institution")
    row=LibraryBook(tenant_id=user.tenant_id,campus_id=payload.campus_id,accession_no=accession,isbn=payload.isbn.strip() if payload.isbn else None,title=payload.title.strip(),author=payload.author.strip(),category=payload.category.strip(),resource_type=payload.resource_type.strip(),publisher=payload.publisher.strip(),edition=payload.edition.strip(),publication_year=payload.publication_year,language=payload.language.strip(),shelf_location=payload.shelf_location.strip(),academic_unit_id=unit.id if unit else None)
    db.add(row); audit(db,user,"CREATE","Library Book",f"{row.accession_no}:{row.title}"); db.commit(); db.refresh(row)
    return {"id":row.id,"accession_no":row.accession_no,"status":row.status}

@app.patch("/api/v1/admin/library/books/{book_id}")
def admin_library_book_update(book_id:int,payload:AdminLibraryBookUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(LibraryBook).where(LibraryBook.id==book_id,LibraryBook.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Library book not found")
    status=payload.status.strip().title()
    if status not in {"Available","Issued","Lost","Damaged","Inactive"}: raise HTTPException(400,"Invalid library book status")
    active_loan=db.scalar(select(LibraryLoan.id).where(LibraryLoan.tenant_id==user.tenant_id,LibraryLoan.book_id==row.id,LibraryLoan.returned_at.is_(None)))
    if active_loan and status!="Issued": raise HTTPException(409,"A book with an active loan must remain Issued")
    if not active_loan and status=="Issued": raise HTTPException(409,"Use the circulation workflow to mark a book as Issued")
    unit=db.get(AcademicUnit,payload.academic_unit_id) if payload.academic_unit_id else None
    if unit and unit.tenant_id!=user.tenant_id: raise HTTPException(400,"Academic unit does not belong to this institution")
    row.title=payload.title.strip(); row.author=payload.author.strip(); row.category=payload.category.strip(); row.isbn=payload.isbn.strip() if payload.isbn else None; row.resource_type=payload.resource_type.strip(); row.publisher=payload.publisher.strip(); row.edition=payload.edition.strip(); row.publication_year=payload.publication_year; row.language=payload.language.strip(); row.shelf_location=payload.shelf_location.strip(); row.academic_unit_id=unit.id if unit else None; row.status=status
    audit(db,user,"UPDATE","Library Book",f"{row.accession_no}:{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.post("/api/v1/admin/library/loans")
def admin_library_issue(payload:AdminLibraryLoanIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    book=db.scalar(select(LibraryBook).where(LibraryBook.id==payload.book_id,LibraryBook.tenant_id==user.tenant_id))
    if not book: raise HTTPException(404,"Library book not found")
    if book.status!="Available": raise HTTPException(409,"Only available books can be issued")
    borrower=db.scalar(select(User).where(User.id==payload.borrower_user_id,User.tenant_id==user.tenant_id,User.is_active==True))
    if not borrower: raise HTTPException(404,"Active borrower not found in this institution")
    if borrower.campus_id!=book.campus_id: raise HTTPException(409,"Borrower and book must belong to the same campus")
    due=_parse_due_at(payload.due_at)
    if not due or due<=dt.datetime.utcnow(): raise HTTPException(400,"Due date must be in the future")
    active=db.scalar(select(LibraryLoan.id).where(LibraryLoan.tenant_id==user.tenant_id,LibraryLoan.book_id==book.id,LibraryLoan.returned_at.is_(None)))
    if active: raise HTTPException(409,"Book already has an active loan")
    active_for_borrower=db.scalars(select(LibraryLoan).where(LibraryLoan.tenant_id==user.tenant_id,LibraryLoan.borrower_user_id==borrower.id,LibraryLoan.returned_at.is_(None))).all()
    limit=5 if borrower.role=="Teacher" else 3
    if len(active_for_borrower)>=limit: raise HTTPException(409,f"Borrower has reached the active loan limit of {limit}")
    row=LibraryLoan(tenant_id=user.tenant_id,campus_id=book.campus_id,book_id=book.id,borrower_user_id=borrower.id,due_at=due,fine_per_day=payload.fine_per_day,status="Issued")
    book.status="Issued"; db.add(row); audit(db,user,"ISSUE","Library Loan",f"book={book.id};borrower={borrower.id}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"due_at":row.due_at}

@app.patch("/api/v1/admin/library/loans/{loan_id}/return")
def admin_library_return(loan_id:int,payload:AdminLibraryReturnIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(LibraryLoan).where(LibraryLoan.id==loan_id,LibraryLoan.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Library loan not found")
    if row.returned_at is not None: raise HTTPException(409,"Book has already been returned")
    book=db.scalar(select(LibraryBook).where(LibraryBook.id==row.book_id,LibraryBook.tenant_id==user.tenant_id))
    if not book: raise HTTPException(409,"Loan book record is unavailable")
    row.returned_at=dt.datetime.utcnow()
    overdue_days=max(0,(row.returned_at.date()-row.due_at.date()).days)
    calculated=round(overdue_days*float(row.fine_per_day or 0),2)
    row.fine_amount=max(payload.fine_amount,calculated); row.return_condition=payload.return_condition.strip().title(); row.fine_status=payload.fine_status.strip().title()
    if row.fine_status not in {"Unpaid","Paid","Waived"}: raise HTTPException(400,"Invalid fine status")
    row.status="Returned"; book.status="Damaged" if row.return_condition=="Damaged" else "Available"
    audit(db,user,"RETURN","Library Loan",f"loan={row.id};book={book.id};fine={payload.fine_amount}"); db.commit()
    return {"id":row.id,"status":row.status,"returned_at":row.returned_at}

@app.get("/api/v1/admin/transport")
def admin_transport(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    routes=db.scalars(select(TransportRoute).where(TransportRoute.tenant_id==user.tenant_id).order_by(TransportRoute.name)).all()
    vehicles=db.scalars(select(TransportVehicle).where(TransportVehicle.tenant_id==user.tenant_id).order_by(TransportVehicle.vehicle_number)).all()
    allocations=db.scalars(select(StudentTransportAllocation).where(StudentTransportAllocation.tenant_id==user.tenant_id)).all()
    stops=db.scalars(select(TransportStop).where(TransportStop.tenant_id==user.tenant_id).order_by(TransportStop.route_id,TransportStop.stop_order)).all()
    eligible_students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Student",User.is_active==True).order_by(User.name)).all()
    route_map={x.id:x for x in routes}; vehicle_map={x.id:x for x in vehicles}; stop_map={x.id:x for x in stops}
    student_ids={x.student_user_id for x in allocations}; students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.id.in_(student_ids))).all() if student_ids else []
    names={x.id:x.name for x in students}
    return {"summary":{"routes":len(routes),"active_routes":sum(x.status=="Active" for x in routes),"vehicles":len(vehicles),"active_vehicles":sum(x.status=="Active" for x in vehicles),"allocations":len(allocations),"active_allocations":sum(x.status=="Active" for x in allocations)},"routes":[{"id":x.id,"campus_id":x.campus_id,"name":x.name,"code":x.code,"status":x.status} for x in routes],"vehicles":[{"id":x.id,"campus_id":x.campus_id,"vehicle_number":x.vehicle_number,"label":x.label,"status":x.status} for x in vehicles],"allocations":[{"id":x.id,"campus_id":x.campus_id,"student_user_id":x.student_user_id,"student_name":names.get(x.student_user_id,f"Student #{x.student_user_id}"),"route_id":x.route_id,"route_name":route_map[x.route_id].name if x.route_id in route_map else "","vehicle_id":x.vehicle_id,"vehicle_number":vehicle_map[x.vehicle_id].vehicle_number if x.vehicle_id in vehicle_map else "","stop_id":x.stop_id,"stop_name":stop_map[x.stop_id].name if x.stop_id in stop_map else "","pickup_time":x.pickup_time,"drop_time":x.drop_time,"status":x.status} for x in allocations],"stops":[{"id":x.id,"route_id":x.route_id,"name":x.name,"stop_order":x.stop_order} for x in stops],"students":[{"id":x.id,"name":x.name,"campus_id":x.campus_id} for x in eligible_students]}

@app.post("/api/v1/admin/transport/routes")
def admin_transport_route_create(payload:AdminTransportRouteIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    if not db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==payload.campus_id).limit(1)): raise HTTPException(404,"Campus not found in this institution")
    code=payload.code.strip()
    if db.scalar(select(TransportRoute.id).where(TransportRoute.tenant_id==user.tenant_id,TransportRoute.campus_id==payload.campus_id,TransportRoute.code==code)): raise HTTPException(409,"Route code already exists for this campus")
    row=TransportRoute(tenant_id=user.tenant_id,campus_id=payload.campus_id,name=payload.name.strip(),code=code)
    db.add(row); audit(db,user,"CREATE","Transport Route",f"{code}:{row.name}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.post("/api/v1/admin/transport/vehicles")
def admin_transport_vehicle_create(payload:AdminTransportVehicleIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    if not db.scalar(select(User.id).where(User.tenant_id==user.tenant_id,User.campus_id==payload.campus_id).limit(1)): raise HTTPException(404,"Campus not found in this institution")
    number=payload.vehicle_number.strip()
    if db.scalar(select(TransportVehicle.id).where(TransportVehicle.tenant_id==user.tenant_id,TransportVehicle.vehicle_number==number)): raise HTTPException(409,"Vehicle number already exists")
    row=TransportVehicle(tenant_id=user.tenant_id,campus_id=payload.campus_id,vehicle_number=number,label=payload.label.strip())
    db.add(row); audit(db,user,"CREATE","Transport Vehicle",number); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.post("/api/v1/admin/transport/stops")
def admin_transport_stop_create(payload:AdminTransportStopIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    route=db.scalar(select(TransportRoute).where(TransportRoute.id==payload.route_id,TransportRoute.tenant_id==user.tenant_id))
    if not route: raise HTTPException(404,"Transport route not found")
    duplicate=db.scalar(select(TransportStop.id).where(TransportStop.tenant_id==user.tenant_id,TransportStop.route_id==route.id,TransportStop.name==payload.name.strip()))
    if duplicate: raise HTTPException(409,"Stop already exists on this route")
    row=TransportStop(tenant_id=user.tenant_id,route_id=route.id,name=payload.name.strip(),stop_order=payload.stop_order)
    db.add(row); audit(db,user,"CREATE","Transport Stop",f"route={route.id};{row.name}"); db.commit(); db.refresh(row)
    return {"id":row.id,"name":row.name}

@app.post("/api/v1/admin/transport/allocations")
def admin_transport_allocation_create(payload:AdminTransportAllocationIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    student=db.scalar(select(User).where(User.id==payload.student_user_id,User.tenant_id==user.tenant_id,User.role=="Student",User.is_active==True))
    route=db.scalar(select(TransportRoute).where(TransportRoute.id==payload.route_id,TransportRoute.tenant_id==user.tenant_id,TransportRoute.status=="Active"))
    stop=db.scalar(select(TransportStop).where(TransportStop.id==payload.stop_id,TransportStop.tenant_id==user.tenant_id,TransportStop.route_id==payload.route_id))
    vehicle=db.scalar(select(TransportVehicle).where(TransportVehicle.id==payload.vehicle_id,TransportVehicle.tenant_id==user.tenant_id,TransportVehicle.status=="Active")) if payload.vehicle_id else None
    if not student: raise HTTPException(404,"Active student not found")
    if not route: raise HTTPException(400,"Invalid active route")
    if not stop: raise HTTPException(400,"Stop does not belong to the selected route")
    if payload.vehicle_id and not vehicle: raise HTTPException(400,"Invalid active vehicle")
    if student.campus_id!=route.campus_id or (vehicle and vehicle.campus_id!=route.campus_id): raise HTTPException(409,"Student, route and vehicle must belong to the same campus")
    existing=db.scalar(select(StudentTransportAllocation).where(StudentTransportAllocation.tenant_id==user.tenant_id,StudentTransportAllocation.student_user_id==student.id))
    if existing: raise HTTPException(409,"Student already has a transport allocation")
    status=payload.status.strip().title()
    if status not in {"Active","Inactive"}: raise HTTPException(400,"Invalid allocation status")
    row=StudentTransportAllocation(tenant_id=user.tenant_id,campus_id=route.campus_id,student_user_id=student.id,route_id=route.id,vehicle_id=vehicle.id if vehicle else None,stop_id=stop.id,pickup_time=payload.pickup_time.strip(),drop_time=payload.drop_time.strip(),status=status)
    db.add(row); audit(db,user,"CREATE","Transport Allocation",f"student={student.id};route={route.id}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.patch("/api/v1/admin/transport/allocations/{allocation_id}")
def admin_transport_allocation_update(allocation_id:int,payload:AdminTransportAllocationIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(StudentTransportAllocation).where(StudentTransportAllocation.id==allocation_id,StudentTransportAllocation.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Transport allocation not found")
    if payload.student_user_id!=row.student_user_id: raise HTTPException(400,"Student cannot be changed on an existing allocation")
    route=db.scalar(select(TransportRoute).where(TransportRoute.id==payload.route_id,TransportRoute.tenant_id==user.tenant_id,TransportRoute.status=="Active"))
    stop=db.scalar(select(TransportStop).where(TransportStop.id==payload.stop_id,TransportStop.tenant_id==user.tenant_id,TransportStop.route_id==payload.route_id))
    vehicle=db.scalar(select(TransportVehicle).where(TransportVehicle.id==payload.vehicle_id,TransportVehicle.tenant_id==user.tenant_id,TransportVehicle.status=="Active")) if payload.vehicle_id else None
    student=db.scalar(select(User).where(User.id==row.student_user_id,User.tenant_id==user.tenant_id,User.role=="Student"))
    if not route or not stop or not student: raise HTTPException(400,"Invalid route, stop or student")
    if payload.vehicle_id and not vehicle: raise HTTPException(400,"Invalid active vehicle")
    if student.campus_id!=route.campus_id or (vehicle and vehicle.campus_id!=route.campus_id): raise HTTPException(409,"Student, route and vehicle must belong to the same campus")
    status=payload.status.strip().title()
    if status not in {"Active","Inactive"}: raise HTTPException(400,"Invalid allocation status")
    row.campus_id=route.campus_id; row.route_id=route.id; row.vehicle_id=vehicle.id if vehicle else None; row.stop_id=stop.id; row.pickup_time=payload.pickup_time.strip(); row.drop_time=payload.drop_time.strip(); row.status=status
    audit(db,user,"UPDATE","Transport Allocation",f"allocation={row.id};route={route.id};status={status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.patch("/api/v1/admin/transport/routes/{route_id}")
def admin_transport_route_update(route_id:int,payload:AdminTransportRouteUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(TransportRoute).where(TransportRoute.id==route_id,TransportRoute.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Route not found")
    status=payload.status.strip().title()
    if status not in {"Active","Inactive"}: raise HTTPException(400,"Invalid route status")
    code=payload.code.strip(); duplicate=db.scalar(select(TransportRoute.id).where(TransportRoute.tenant_id==user.tenant_id,TransportRoute.campus_id==row.campus_id,TransportRoute.code==code,TransportRoute.id!=row.id))
    if duplicate: raise HTTPException(409,"Route code already exists for this campus")
    row.name=payload.name.strip(); row.code=code; row.status=status; audit(db,user,"UPDATE","Transport Route",f"{row.code}:{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.patch("/api/v1/admin/transport/vehicles/{vehicle_id}")
def admin_transport_vehicle_update(vehicle_id:int,payload:AdminTransportVehicleUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(TransportVehicle).where(TransportVehicle.id==vehicle_id,TransportVehicle.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Vehicle not found")
    status=payload.status.strip().title()
    if status not in {"Active","Inactive"}: raise HTTPException(400,"Invalid vehicle status")
    number=payload.vehicle_number.strip(); duplicate=db.scalar(select(TransportVehicle.id).where(TransportVehicle.tenant_id==user.tenant_id,TransportVehicle.vehicle_number==number,TransportVehicle.id!=row.id))
    if duplicate: raise HTTPException(409,"Vehicle number already exists")
    row.vehicle_number=number; row.label=payload.label.strip(); row.status=status; audit(db,user,"UPDATE","Transport Vehicle",f"{row.vehicle_number}:{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/grievances")
def admin_grievances(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id).order_by(Grievance.created_at.desc())).all()
    creators={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()}
    return {"summary":{"total":len(rows),"open":sum(x.status=="Open" for x in rows),"in_progress":sum(x.status=="In Progress" for x in rows),"resolved":sum(x.status in {"Resolved","Closed"} for x in rows),"urgent":sum(x.priority=="Urgent" and x.status not in {"Resolved","Closed"} for x in rows)},"grievances":[{"id":x.id,"ticket_no":x.ticket_no,"creator_name":creators[x.created_by_user_id].name if x.created_by_user_id in creators else f"User #{x.created_by_user_id}","creator_role":creators[x.created_by_user_id].role if x.created_by_user_id in creators else "Unknown","campus_id":x.campus_id,"category":x.category,"subject":x.subject,"details":x.details,"priority":x.priority,"status":x.status,"latest_update":x.latest_update,"created_at":x.created_at,"updated_at":x.updated_at} for x in rows]}

@app.patch("/api/v1/admin/grievances/{grievance_id}")
def admin_grievance_update(grievance_id:int,payload:CampusGrievanceUpdateIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(Grievance).where(Grievance.id==grievance_id,Grievance.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Grievance not found")
    status=payload.status.strip()
    if status not in {"Open","In Progress","Resolved","Closed"}: raise HTTPException(400,"Invalid grievance status")
    row.status=status; row.latest_update=payload.latest_update.strip(); row.updated_at=dt.datetime.utcnow()
    audit(db,user,"GRIEVANCE_UPDATE",f"grievance:{row.id}",f"ticket={row.ticket_no};status={status}"); db.commit()
    return {"id":row.id,"status":row.status,"latest_update":row.latest_update}

@app.get("/api/v1/admin/events")
def admin_events(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(AcademyEvent).where(AcademyEvent.tenant_id==user.tenant_id).order_by(AcademyEvent.starts_at.desc())).all()
    registrations=db.scalars(select(EventRegistration).where(EventRegistration.tenant_id==user.tenant_id)).all()
    reg_counts={}
    for r in registrations: reg_counts[r.event_id]=reg_counts.get(r.event_id,0)+1
    users={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()}
    now=dt.datetime.utcnow()
    return {"summary":{"events":len(rows),"published":sum(x.status=="Published" for x in rows),"upcoming":sum(x.ends_at>=now for x in rows),"registration_required":sum(bool(x.registration_required) for x in rows),"registrations":len(registrations)},"events":[{"id":x.id,"title":x.title,"event_type":x.event_type,"venue":x.venue,"starts_at":x.starts_at,"ends_at":x.ends_at,"audience_role":x.audience_role,"registration_required":x.registration_required,"registration_deadline":x.registration_deadline,"status":x.status,"campus_id":x.campus_id,"organizer":users[x.organizer_user_id].name if x.organizer_user_id in users else f"User #{x.organizer_user_id}","registrations":reg_counts.get(x.id,0)} for x in rows]}

@app.post("/api/v1/admin/events")
def admin_event_create(payload:CampusEventIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    try:
        starts=dt.datetime.fromisoformat(payload.starts_at); ends=dt.datetime.fromisoformat(payload.ends_at)
        deadline=dt.datetime.fromisoformat(payload.registration_deadline) if payload.registration_deadline else None
    except ValueError: raise HTTPException(400,"Invalid event date/time")
    if ends<=starts: raise HTTPException(400,"Event end must be after start")
    if payload.audience_role not in {"ALL","Student","Teacher","Parent","Parent / Guardian"}: raise HTTPException(400,"Invalid audience role")
    if deadline and deadline>starts: raise HTTPException(400,"Registration deadline must be before event start")
    row=AcademyEvent(tenant_id=user.tenant_id,campus_id=user.campus_id,title=payload.title,event_type=payload.event_type,venue=payload.venue,starts_at=starts,ends_at=ends,organizer_user_id=user.id,audience_role=payload.audience_role,registration_required=payload.registration_required,registration_deadline=deadline,status="Published")
    db.add(row); audit(db,user,"EVENT_CREATE","institution_event",payload.title); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.put("/api/v1/admin/events/{event_id}")
def admin_event_update(event_id:int,payload:AdminEventUpdateIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(AcademyEvent).where(AcademyEvent.id==event_id,AcademyEvent.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Event not found")
    try:
        starts=dt.datetime.fromisoformat(payload.starts_at); ends=dt.datetime.fromisoformat(payload.ends_at)
        deadline=dt.datetime.fromisoformat(payload.registration_deadline) if payload.registration_deadline else None
    except ValueError: raise HTTPException(400,"Invalid event date/time")
    if ends<=starts: raise HTTPException(400,"Event end must be after start")
    if deadline and deadline>starts: raise HTTPException(400,"Registration deadline must be before event start")
    if payload.audience_role not in {"ALL","Student","Teacher","Parent","Parent / Guardian"}: raise HTTPException(400,"Invalid audience role")
    status=payload.status.strip().title()
    if status not in {"Published","Draft","Cancelled","Completed"}: raise HTTPException(400,"Invalid event status")
    row.title=payload.title.strip(); row.event_type=payload.event_type.strip(); row.venue=payload.venue.strip(); row.starts_at=starts; row.ends_at=ends; row.audience_role=payload.audience_role; row.registration_required=payload.registration_required; row.registration_deadline=deadline; row.status=status
    audit(db,user,"EVENT_UPDATE","institution_event",f"{row.id}:{row.title}:{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/lms-overview")
def admin_lms_overview(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    works=db.scalars(select(AcademicWork).where(AcademicWork.tenant_id==user.tenant_id).order_by(AcademicWork.id.desc())).all()
    submissions=db.scalars(select(StudentAcademicWork).where(StudentAcademicWork.tenant_id==user.tenant_id)).all()
    units={x.id:x for x in db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id)).all()}
    teachers={x.id:x for x in db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Teacher")).all()}
    by_work={}
    for s in submissions: by_work.setdefault(s.work_id,[]).append(s)
    counts={}
    rows=[]
    for w in works:
        counts[w.work_type]=counts.get(w.work_type,0)+1; subs=by_work.get(w.id,[])
        rows.append({"id":w.id,"work_type":w.work_type,"title":w.title,"description":w.description,"unit_id":w.unit_id,"unit_name":units[w.unit_id].name if w.unit_id in units else f"Unit #{w.unit_id}","teacher_user_id":w.teacher_user_id,"teacher_name":teachers[w.teacher_user_id].name if w.teacher_user_id in teachers else f"Teacher #{w.teacher_user_id}","max_marks":w.max_marks,"due_at":w.due_at,"status":w.status,"submissions":sum(s.status in {"SUBMITTED","GRADED"} for s in subs),"graded":sum(s.status=="GRADED" for s in subs)})
    available_units=[x for x in units.values() if x.unit_type in {"COURSE","SECTION_BATCH"} and x.status=="Active"]
    available_teachers=[x for x in teachers.values() if x.is_active]
    return {"summary":{"learning_items":len(works),"homework":counts.get("HOMEWORK",0),"assignments":counts.get("ASSIGNMENT",0),"exams":counts.get("EXAM",0),"submissions":sum(s.status in {"SUBMITTED","GRADED"} for s in submissions),"graded":sum(s.status=="GRADED" for s in submissions)},"items":rows,"units":[{"id":x.id,"name":x.name,"code":x.code,"campus_id":x.campus_id} for x in available_units],"teachers":[{"id":x.id,"name":x.name,"campus_id":x.campus_id} for x in available_teachers]}

def _admin_lms_context(db,user,unit_id,teacher_id):
    unit=db.scalar(select(AcademicUnit).where(AcademicUnit.id==unit_id,AcademicUnit.tenant_id==user.tenant_id))
    teacher=db.scalar(select(User).where(User.id==teacher_id,User.tenant_id==user.tenant_id,User.role=="Teacher",User.is_active==True))
    if not unit or unit.unit_type not in {"COURSE","SECTION_BATCH"}: raise HTTPException(400,"Invalid course or section")
    if not teacher: raise HTTPException(400,"Invalid active teacher")
    if unit.campus_id!=teacher.campus_id: raise HTTPException(409,"Teacher and academic unit must belong to the same campus")
    return unit,teacher

@app.post("/api/v1/admin/lms")
def admin_lms_create(payload:AdminAcademicWorkIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    kind=payload.work_type.strip().upper()
    if kind not in {"HOMEWORK","ASSIGNMENT"}: raise HTTPException(400,"Use Exams & Results to create exams")
    _admin_lms_context(db,user,payload.unit_id,payload.teacher_user_id)
    row=AcademicWork(tenant_id=user.tenant_id,unit_id=payload.unit_id,teacher_user_id=payload.teacher_user_id,work_type=kind,title=payload.title.strip(),description=payload.description.strip(),max_marks=payload.max_marks,due_at=_parse_due_at(payload.due_at),status="PUBLISHED")
    db.add(row); audit(db,user,"CREATE_ADMIN",kind,row.title); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.put("/api/v1/admin/lms/{work_id}")
def admin_lms_update(work_id:int,payload:AdminAcademicWorkUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(AcademicWork).where(AcademicWork.id==work_id,AcademicWork.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Learning item not found")
    if row.work_type=="EXAM": raise HTTPException(400,"Manage exams from Exams & Results")
    _admin_lms_context(db,user,row.unit_id,payload.teacher_user_id)
    status=payload.status.strip().upper()
    if status not in {"PUBLISHED","DRAFT","CLOSED"}: raise HTTPException(400,"Invalid learning item status")
    graded=db.scalars(select(StudentAcademicWork).where(StudentAcademicWork.tenant_id==user.tenant_id,StudentAcademicWork.work_id==row.id,StudentAcademicWork.status=="GRADED")).all()
    if graded and any(float(x.marks or 0)>payload.max_marks for x in graded): raise HTTPException(409,"Maximum marks cannot be lower than an existing graded submission")
    row.teacher_user_id=payload.teacher_user_id; row.title=payload.title.strip(); row.description=payload.description.strip(); row.max_marks=payload.max_marks; row.due_at=_parse_due_at(payload.due_at); row.status=status
    audit(db,user,"UPDATE_ADMIN",row.work_type,f"{row.id}:{row.title}:{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/communication")
def admin_communication(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    rows=db.scalars(select(CommunicationMessage).where(CommunicationMessage.tenant_id==user.tenant_id).order_by(CommunicationMessage.created_at.desc()).limit(500)).all()
    result=[]; sent_by_role={}; to_role={}
    for row in rows:
        sender=db.get(User,row.sender_user_id); recipient=db.get(User,row.recipient_user_id); student=db.get(User,row.student_user_id) if row.student_user_id else None
        sr=sender.role if sender and sender.tenant_id==user.tenant_id else "Unknown"; rr=recipient.role if recipient and recipient.tenant_id==user.tenant_id else "Unknown"
        sent_by_role[sr]=sent_by_role.get(sr,0)+1; to_role[rr]=to_role.get(rr,0)+1
        result.append({"id":row.id,"sender_user_id":row.sender_user_id,"sender":sender.name if sender and sender.tenant_id==user.tenant_id else "Unknown","sender_role":sr,"recipient_user_id":row.recipient_user_id,"recipient":recipient.name if recipient and recipient.tenant_id==user.tenant_id else "Unknown","recipient_role":rr,"student_user_id":row.student_user_id,"student_name":student.name if student and student.tenant_id==user.tenant_id else None,"subject":row.subject,"body":row.body,"status":row.status,"created_at":row.created_at})
    recipients=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.is_active==True,User.id!=user.id).order_by(User.role,User.name)).all()
    return {"summary":{"messages":len(rows),"teacher_sent":sent_by_role.get("Teacher",0),"parent_sent":sent_by_role.get("Parent / Guardian",0),"to_students":to_role.get("Student",0),"to_parents":to_role.get("Parent / Guardian",0)},"messages":result,"recipients":[{"id":x.id,"name":x.name,"role":x.role,"email":x.email,"campus_id":x.campus_id} for x in recipients]}

@app.post("/api/v1/admin/communication")
def admin_send_message(payload:TeacherMessageIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    recipient=db.scalar(select(User).where(User.id==payload.recipient_user_id,User.tenant_id==user.tenant_id,User.is_active==True))
    if not recipient: raise HTTPException(404,"Recipient not found in this institution")
    student=None
    if payload.student_user_id is not None:
        student=db.scalar(select(User).where(User.id==payload.student_user_id,User.tenant_id==user.tenant_id,User.role=="Student"))
        if not student: raise HTTPException(400,"Invalid student context")
        if recipient.role=="Student" and recipient.id!=student.id: raise HTTPException(409,"Student context must match the student recipient")
        if recipient.role=="Parent / Guardian":
            linked=db.scalar(select(ParentStudentLink.id).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.parent_user_id==recipient.id,ParentStudentLink.student_user_id==student.id))
            if not linked: raise HTTPException(409,"Selected student is not linked to this parent or guardian")
    row=CommunicationMessage(tenant_id=user.tenant_id,sender_user_id=user.id,recipient_user_id=recipient.id,student_user_id=student.id if student else None,subject=payload.subject.strip(),body=payload.body.strip())
    db.add(row); audit(db,user,"MESSAGE_ADMIN","Communication",f"to={recipient.id};{row.subject}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status,"created_at":row.created_at}

@app.put("/api/v1/admin/communication/{message_id}")
def admin_update_message(message_id:int,payload:TeacherMessageIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(CommunicationMessage).where(CommunicationMessage.id==message_id,CommunicationMessage.tenant_id==user.tenant_id,CommunicationMessage.sender_user_id==user.id))
    if not row: raise HTTPException(404,"Editable institution message not found")
    recipient=db.scalar(select(User).where(User.id==payload.recipient_user_id,User.tenant_id==user.tenant_id,User.is_active==True))
    if not recipient: raise HTTPException(404,"Recipient not found in this institution")
    student=None
    if payload.student_user_id is not None:
        student=db.scalar(select(User).where(User.id==payload.student_user_id,User.tenant_id==user.tenant_id,User.role=="Student"))
        if not student: raise HTTPException(400,"Invalid student context")
        if recipient.role=="Student" and recipient.id!=student.id: raise HTTPException(409,"Student context must match the student recipient")
        if recipient.role=="Parent / Guardian" and not db.scalar(select(ParentStudentLink.id).where(ParentStudentLink.tenant_id==user.tenant_id,ParentStudentLink.parent_user_id==recipient.id,ParentStudentLink.student_user_id==student.id)): raise HTTPException(409,"Selected student is not linked to this parent or guardian")
    row.recipient_user_id=recipient.id; row.student_user_id=student.id if student else None; row.subject=payload.subject.strip(); row.body=payload.body.strip()
    audit(db,user,"UPDATE","Communication",f"message={row.id};to={recipient.id}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/exams-results")
def admin_exams_results(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    exams=db.scalars(select(AcademicWork).where(AcademicWork.tenant_id==user.tenant_id,AcademicWork.work_type=="EXAM").order_by(AcademicWork.id.desc())).all()
    results=db.scalars(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id)).all()
    by_exam={}
    for r in results: by_exam.setdefault(r.work_id,[]).append(r)
    rows=[]
    for exam in exams:
        unit=db.get(AcademicUnit,exam.unit_id); teacher=db.get(User,exam.teacher_user_id); saved=by_exam.get(exam.id,[])
        passed=sum(r.result_status=="PASS" for r in saved); failed=sum(r.result_status=="FAIL" for r in saved); published=sum(bool(r.published) for r in saved)
        avg=round(sum(r.percentage for r in saved)/len(saved),1) if saved else None
        rows.append({"id":exam.id,"title":exam.title,"unit_name":unit.name if unit else f"Unit #{exam.unit_id}","teacher_name":teacher.name if teacher else f"Teacher #{exam.teacher_user_id}","max_marks":exam.max_marks,"due_at":exam.due_at,"results":len(saved),"passed":passed,"failed":failed,"published":published,"average_percentage":avg,"status":"PUBLISHED" if saved and published==len(saved) else "DRAFT" if saved else "AWAITING RESULTS"})
    published_results=sum(bool(r.published) for r in results)
    pass_count=sum(r.result_status=="PASS" for r in results)
    units=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.unit_type.in_({"COURSE","SECTION_BATCH"}),AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    teachers=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Teacher",User.is_active==True).order_by(User.name)).all()
    return {"summary":{"exams":len(exams),"results":len(results),"published":published_results,"draft":len(results)-published_results,"pass_rate":round(pass_count*100/len(results),1) if results else None},"exams":rows,"units":[{"id":x.id,"name":x.name,"code":x.code,"campus_id":x.campus_id} for x in units],"teachers":[{"id":x.id,"name":x.name,"campus_id":x.campus_id} for x in teachers]}

@app.post("/api/v1/admin/exams")
def admin_exam_create(payload:AcademicWorkIn,teacher_user_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    unit=db.scalar(select(AcademicUnit).where(AcademicUnit.id==payload.unit_id,AcademicUnit.tenant_id==user.tenant_id))
    teacher=db.scalar(select(User).where(User.id==teacher_user_id,User.tenant_id==user.tenant_id,User.role=="Teacher",User.is_active==True))
    if not unit or unit.unit_type not in {"COURSE","SECTION_BATCH"}: raise HTTPException(400,"Invalid exam course or section")
    if not teacher: raise HTTPException(400,"Invalid active teacher")
    if unit.campus_id!=teacher.campus_id: raise HTTPException(409,"Teacher and exam unit must belong to the same campus")
    if payload.max_marks<=0: raise HTTPException(400,"Exam maximum marks must be greater than zero")
    due=_parse_due_at(payload.due_at)
    row=AcademicWork(tenant_id=user.tenant_id,unit_id=unit.id,teacher_user_id=teacher.id,work_type="EXAM",title=payload.title.strip(),description=payload.description.strip(),max_marks=payload.max_marks,due_at=due)
    db.add(row); audit(db,user,"CREATE","EXAM",f"{row.title};teacher={teacher.id}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/exams/{work_id}/results")
def admin_exam_results(work_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    exam=db.scalar(select(AcademicWork).where(AcademicWork.id==work_id,AcademicWork.tenant_id==user.tenant_id,AcademicWork.work_type=="EXAM"))
    if not exam: raise HTTPException(404,"Exam not found")
    students=sorted(_students_for_unit(db,user.tenant_id,exam.unit_id)); saved={r.student_user_id:r for r in db.scalars(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id,ExamResult.work_id==work_id)).all()}
    rows=[]
    for sid in students:
        st=db.scalar(select(User).where(User.id==sid,User.tenant_id==user.tenant_id,User.role=="Student")); r=saved.get(sid)
        if st: rows.append({"student_id":sid,"student_name":st.name,"marks":r.marks if r else None,"percentage":r.percentage if r else None,"grade":r.grade if r else "","result_status":r.result_status if r else "","remarks":r.remarks if r else "","published":bool(r.published) if r else False})
    return {"exam":{"id":exam.id,"title":exam.title,"max_marks":exam.max_marks},"students":rows}

@app.put("/api/v1/admin/exams/{work_id}/results")
def admin_exam_result_save(work_id:int,payload:ExamResultIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    exam=db.scalar(select(AcademicWork).where(AcademicWork.id==work_id,AcademicWork.tenant_id==user.tenant_id,AcademicWork.work_type=="EXAM"))
    if not exam: raise HTTPException(404,"Exam not found")
    if payload.student_user_id not in _students_for_unit(db,user.tenant_id,exam.unit_id): raise HTTPException(400,"Student is not enrolled in this exam course")
    if exam.max_marks<=0: raise HTTPException(409,"Exam maximum marks must be greater than zero before results can be entered")
    if payload.marks>exam.max_marks: raise HTTPException(400,"Marks cannot exceed maximum marks")
    percentage=round(payload.marks*100/exam.max_marks,2); rule=_grade_for(db,user.tenant_id,percentage)
    if not rule: raise HTTPException(409,"No grading rule covers this percentage")
    row=db.scalar(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id,ExamResult.work_id==work_id,ExamResult.student_user_id==payload.student_user_id))
    if row and row.published: raise HTTPException(409,"Published results are locked")
    if not row: row=ExamResult(tenant_id=user.tenant_id,work_id=work_id,student_user_id=payload.student_user_id,marks=payload.marks,percentage=percentage,grade=rule.grade,grade_point=rule.grade_point,result_status=rule.result_status,remarks=payload.remarks); db.add(row)
    else: row.marks=payload.marks; row.percentage=percentage; row.grade=rule.grade; row.grade_point=rule.grade_point; row.result_status=rule.result_status; row.remarks=payload.remarks
    audit(db,user,"GRADE_ADMIN","exam_result",f"exam={work_id};student={payload.student_user_id};grade={rule.grade}"); db.commit()
    return {"ok":True,"grade":rule.grade,"percentage":percentage}

@app.post("/api/v1/admin/exams/{work_id}/approve")
def admin_exam_approve(work_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    exam=db.scalar(select(AcademicWork).where(AcademicWork.id==work_id,AcademicWork.tenant_id==user.tenant_id,AcademicWork.work_type=="EXAM"))
    if not exam: raise HTTPException(404,"Exam not found")
    gaps=_grading_scheme_gaps(db,user.tenant_id)
    if gaps: raise HTTPException(409,"Complete the grading scheme before approving results")
    student_ids=_students_for_unit(db,user.tenant_id,exam.unit_id)
    rows=db.scalars(select(ExamResult).where(ExamResult.tenant_id==user.tenant_id,ExamResult.work_id==work_id)).all()
    if not student_ids: raise HTTPException(409,"No enrolled students for this exam")
    if student_ids-{r.student_user_id for r in rows}: raise HTTPException(409,"Enter results for all enrolled students before approval")
    active_rows=[r for r in rows if r.student_user_id in student_ids]
    if active_rows and all(r.published for r in active_rows): return {"ok":True,"published":len(active_rows),"already_published":True}
    for r in active_rows: r.published=True
    audit(db,user,"APPROVE","exam_results",f"exam={work_id};count={len(active_rows)}"); db.commit()
    return {"ok":True,"published":len(active_rows)}

@app.get("/api/v1/admin/attendance-overview")
def admin_attendance_overview(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    entries=db.scalars(select(AttendanceEntry).where(AttendanceEntry.tenant_id==user.tenant_id).order_by(AttendanceEntry.marked_at.desc())).all()
    students=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Student")).all()
    names={x.id:x.name for x in students}
    sessions={x.id:x for x in db.scalars(select(ClassSession).where(ClassSession.tenant_id==user.tenant_id)).all()}
    units={x.id:x for x in db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id)).all()}
    counts={}
    for x in entries: counts[x.status]=counts.get(x.status,0)+1
    counted=counts.get("PRESENT",0)+counts.get("ABSENT",0)+counts.get("LATE",0)
    attended=counts.get("PRESENT",0)+counts.get("LATE",0)
    rows=[]
    for x in entries[:500]:
        session=sessions.get(x.session_id); unit=units.get(session.unit_id) if session else None
        rows.append({"id":x.id,"student_user_id":x.student_user_id,"student_name":names.get(x.student_user_id,f"Student #{x.student_user_id}"),"session_id":x.session_id,"session_title":session.title if session else f"Session #{x.session_id}","unit_name":unit.name if unit else "—","status":x.status,"note":x.note,"marked_at":x.marked_at})
    admin_sessions=db.scalars(select(ClassSession).where(ClassSession.tenant_id==user.tenant_id).order_by(ClassSession.starts_at.desc()).limit(200)).all()
    return {"summary":{"records":len(entries),"present":counts.get("PRESENT",0),"absent":counts.get("ABSENT",0),"late":counts.get("LATE",0),"excused":counts.get("EXCUSED",0),"attendance_percentage":round(attended*100/counted,1) if counted else None},"entries":rows,"sessions":[{"id":x.id,"title":x.title,"unit_id":x.unit_id,"starts_at":x.starts_at,"status":x.status} for x in admin_sessions]}

@app.get("/api/v1/admin/attendance/{session_id}")
def admin_session_attendance(session_id:int,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    session=db.scalar(select(ClassSession).where(ClassSession.id==session_id,ClassSession.tenant_id==user.tenant_id))
    if not session: raise HTTPException(404,"Class session not found")
    students=_students_for_unit(db,user.tenant_id,session.unit_id)
    result=[]
    for sid in students:
        student=db.scalar(select(User).where(User.id==sid,User.tenant_id==user.tenant_id,User.role=="Student"))
        if not student: continue
        entry=db.scalar(select(AttendanceEntry).where(AttendanceEntry.tenant_id==user.tenant_id,AttendanceEntry.session_id==session.id,AttendanceEntry.student_user_id==sid))
        result.append({"student_user_id":sid,"student_name":student.name,"status":entry.status if entry else "UNMARKED","note":entry.note if entry else ""})
    return {"session":{"id":session.id,"title":session.title,"starts_at":session.starts_at},"students":result}

@app.put("/api/v1/admin/attendance/{session_id}")
def admin_mark_attendance(session_id:int,payload:AttendanceMarkIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    session=db.scalar(select(ClassSession).where(ClassSession.id==session_id,ClassSession.tenant_id==user.tenant_id))
    if not session: raise HTTPException(404,"Class session not found")
    if payload.student_user_id not in _students_for_unit(db,user.tenant_id,session.unit_id): raise HTTPException(400,"Student is not enrolled in this class")
    status=payload.status.strip().upper()
    if status not in {"PRESENT","ABSENT","LATE","EXCUSED"}: raise HTTPException(400,"Invalid attendance status")
    entry=db.scalar(select(AttendanceEntry).where(AttendanceEntry.tenant_id==user.tenant_id,AttendanceEntry.session_id==session.id,AttendanceEntry.student_user_id==payload.student_user_id))
    if not entry:
        entry=AttendanceEntry(tenant_id=user.tenant_id,session_id=session.id,student_user_id=payload.student_user_id,marked_by=user.id); db.add(entry)
    entry.status=status; entry.note=payload.note.strip(); entry.marked_by=user.id; entry.marked_at=dt.datetime.utcnow()
    audit(db,user,"ATTENDANCE_ADMIN",f"session:{session.id}",f"student={payload.student_user_id}:{status}"); db.commit()
    return {"ok":True,"status":status}

@app.get("/api/v1/admin/timetable")
def admin_timetable(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    sessions=db.scalars(select(ClassSession).where(ClassSession.tenant_id==user.tenant_id).order_by(ClassSession.starts_at.desc())).all()
    now=dt.datetime.utcnow()
    rows=[]
    for x in sessions:
        unit=db.get(AcademicUnit,x.unit_id); teacher=db.get(User,x.teacher_user_id)
        rows.append({"id":x.id,"title":x.title,"unit_id":x.unit_id,"unit_name":unit.name if unit else f"Unit #{x.unit_id}","unit_type":unit.unit_type if unit else "","teacher_id":x.teacher_user_id,"teacher_name":teacher.name if teacher else f"Teacher #{x.teacher_user_id}","starts_at":x.starts_at,"ends_at":x.ends_at,"room":x.room,"status":x.status})
    future=[x for x in sessions if x.ends_at>=now]
    rooms=len({x.room for x in future if x.room})
    teachers=len({x.teacher_user_id for x in future})
    units=len({x.unit_id for x in future})
    available_units=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id,AcademicUnit.unit_type.in_({"COURSE","SECTION_BATCH"}),AcademicUnit.status=="Active").order_by(AcademicUnit.name)).all()
    available_teachers=db.scalars(select(User).where(User.tenant_id==user.tenant_id,User.role=="Teacher",User.is_active==True).order_by(User.name)).all()
    return {"summary":{"total":len(sessions),"upcoming":len(future),"teachers":teachers,"academic_units":units,"rooms":rooms},"sessions":rows,"units":[{"id":x.id,"name":x.name,"code":x.code,"unit_type":x.unit_type,"campus_id":x.campus_id} for x in available_units],"teachers":[{"id":x.id,"name":x.name,"email":x.email,"campus_id":x.campus_id} for x in available_teachers]}

def _validate_admin_session(db,user,unit_id,teacher_id,start,end,room,exclude_id=None):
    unit=db.scalar(select(AcademicUnit).where(AcademicUnit.id==unit_id,AcademicUnit.tenant_id==user.tenant_id))
    teacher=db.scalar(select(User).where(User.id==teacher_id,User.tenant_id==user.tenant_id,User.role=="Teacher",User.is_active==True))
    if not unit or unit.unit_type not in {"COURSE","SECTION_BATCH"}: raise HTTPException(400,"Invalid course or section")
    if not teacher: raise HTTPException(400,"Invalid active teacher")
    if unit.campus_id!=teacher.campus_id: raise HTTPException(409,"Teacher and academic unit must belong to the same campus")
    overlap=select(ClassSession).where(ClassSession.tenant_id==user.tenant_id,ClassSession.starts_at<end,ClassSession.ends_at>start)
    if exclude_id is not None: overlap=overlap.where(ClassSession.id!=exclude_id)
    if db.scalar(overlap.where(ClassSession.teacher_user_id==teacher.id)): raise HTTPException(409,"Teacher already has an overlapping class session")
    if db.scalar(overlap.where(ClassSession.unit_id==unit.id)): raise HTTPException(409,"Academic unit already has an overlapping class session")
    if room and db.scalar(overlap.where(ClassSession.room==room)): raise HTTPException(409,"Room is already booked for this time")
    return unit,teacher

@app.post("/api/v1/admin/timetable")
def admin_timetable_create(payload:AdminClassSessionIn,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    start=_parse_due_at(payload.starts_at); end=_parse_due_at(payload.ends_at)
    if not start or not end or end<=start: raise HTTPException(400,"Session end time must be after start time")
    room=payload.room.strip(); _validate_admin_session(db,user,payload.unit_id,payload.teacher_user_id,start,end,room)
    row=ClassSession(tenant_id=user.tenant_id,unit_id=payload.unit_id,teacher_user_id=payload.teacher_user_id,title=payload.title.strip(),starts_at=start,ends_at=end,room=room)
    db.add(row); audit(db,user,"CREATE","class_session",f"{row.title};teacher={payload.teacher_user_id}"); db.commit(); db.refresh(row)
    return {"id":row.id,"status":row.status}

@app.put("/api/v1/admin/timetable/{session_id}")
def admin_timetable_update(session_id:int,payload:AdminClassSessionUpdate,user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    row=db.scalar(select(ClassSession).where(ClassSession.id==session_id,ClassSession.tenant_id==user.tenant_id))
    if not row: raise HTTPException(404,"Class session not found")
    start=_parse_due_at(payload.starts_at); end=_parse_due_at(payload.ends_at)
    if not start or not end or end<=start: raise HTTPException(400,"Session end time must be after start time")
    status=payload.status.strip().title()
    if status not in {"Scheduled","Completed","Cancelled"}: raise HTTPException(400,"Invalid session status")
    room=payload.room.strip(); _validate_admin_session(db,user,row.unit_id,payload.teacher_user_id,start,end,room,row.id)
    row.teacher_user_id=payload.teacher_user_id; row.title=payload.title.strip(); row.starts_at=start; row.ends_at=end; row.room=room; row.status=status
    audit(db,user,"UPDATE","class_session",f"{row.id};{status}"); db.commit()
    return {"id":row.id,"status":row.status}

@app.get("/api/v1/admin/academics-overview")
def admin_academics_overview(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    units=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id).order_by(AcademicUnit.unit_type,AcademicUnit.name)).all()
    assignments=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id,AcademicAssignment.status=="Active")).all()
    users=db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()
    students={x.id:x for x in users if x.role=="Student"}
    teachers={x.id:x for x in users if x.role=="Teacher"}
    counts={}
    for x in units: counts[x.unit_type]=counts.get(x.unit_type,0)+1
    assigned_students=len({x.user_id for x in assignments if x.user_id in students})
    assigned_teachers=len({x.user_id for x in assignments if x.user_id in teachers})
    rows=[]
    for unit in units:
        linked=[x for x in assignments if x.unit_id==unit.id]
        parent=db.get(AcademicUnit,unit.parent_id) if unit.parent_id else None
        rows.append({"id":unit.id,"unit_type":unit.unit_type,"name":unit.name,"code":unit.code,"parent":parent.name if parent else "—","status":unit.status,"assignments":len(linked),"students":sum(x.user_id in students for x in linked),"teachers":sum(x.user_id in teachers for x in linked)})
    return {"summary":{"units":len(units),"programs":counts.get("PROGRAM",0),"courses":counts.get("COURSE",0),"sections":counts.get("SECTION_BATCH",0),"assigned_students":assigned_students,"unassigned_students":max(0,len(students)-assigned_students),"assigned_teachers":assigned_teachers,"unassigned_teachers":max(0,len(teachers)-assigned_teachers)},"type_counts":counts,"units":rows}

@app.get("/api/v1/admin/reports")
def admin_reports(user:User=Depends(require_roles("Institution Admin")),db:Session=Depends(get_db)):
    users=db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()
    students=[x for x in users if x.role=="Student"]
    staff=[x for x in users if x.role in {"Teacher","Accounts","HR","Campus Admin","Auditor"}]
    units=db.scalars(select(AcademicUnit).where(AcademicUnit.tenant_id==user.tenant_id)).all()
    assignments=db.scalars(select(AcademicAssignment).where(AcademicAssignment.tenant_id==user.tenant_id)).all()
    attendance=db.scalars(select(AttendanceEntry).where(AttendanceEntry.tenant_id==user.tenant_id)).all()
    fees=db.scalars(select(FeeLedger).where(FeeLedger.tenant_id==user.tenant_id)).all()
    payments=db.scalars(select(FeePayment).where(FeePayment.tenant_id==user.tenant_id)).all()
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id)).all()
    events=db.scalars(select(AcademyEvent).where(AcademyEvent.tenant_id==user.tenant_id)).all()
    audits=db.scalars(select(Audit).where(Audit.tenant_id==user.tenant_id)).all()
    due=sum(float(x.amount_due or 0) for x in fees)
    paid=sum(float(x.amount_paid or 0) for x in fees)
    reports=[
      {"key":"students","name":"Student & Enrollment Report","category":"Academics","records":len(students),"detail":f"{len(assignments)} academic assignments across {len(units)} units"},
      {"key":"staff","name":"Staff & Role Report","category":"Administration","records":len(staff),"detail":f"{sum(x.is_active for x in staff)} active staff accounts"},
      {"key":"attendance","name":"Attendance Report","category":"Academics","records":len(attendance),"detail":f"{sum(x.status=='PRESENT' for x in attendance)} present entries recorded"},
      {"key":"finance","name":"Fees & Collection Report","category":"Finance","records":len(fees),"detail":f"Due {due:.2f} • Paid {paid:.2f} • {len(payments)} payments"},
      {"key":"grievances","name":"Grievance Report","category":"Operations","records":len(grievances),"detail":f"{sum(x.status in {'Open','In Progress'} for x in grievances)} open/in progress"},
      {"key":"events","name":"Events Report","category":"Operations","records":len(events),"detail":"Institution events and registrations overview"},
      {"key":"audit","name":"Audit Activity Report","category":"Governance","records":len(audits),"detail":"Recorded privileged and operational actions"},
    ]
    return {"summary":{"students":len(students),"staff":len(staff),"academic_units":len(units),"fee_collection":paid,"open_grievances":sum(x.status in {"Open","In Progress"} for x in grievances)},"reports":reports}

@app.get("/api/v1/auditor/dashboard")
def auditor_dashboard(user:User=Depends(require_roles("Auditor")),db:Session=Depends(get_db)):
    audits=db.scalars(select(Audit).where(Audit.tenant_id==user.tenant_id).order_by(Audit.id.desc())).all()
    users=db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id)).all()
    return {
        "users":{"total":len(users),"active":sum(x.is_active for x in users)},
        "audit":{"total_events":len(audits),"recent_events":[{"id":x.id,"actor":x.actor,"action":x.action,"resource":x.resource,"details":x.details,"created_at":x.created_at} for x in audits[:10]]},
        "grievances":{"open":sum(x.status in {"Open","In Progress"} for x in grievances),"resolved":sum(x.status in {"Resolved","Closed"} for x in grievances)},
    }

@app.get("/api/v1/auditor/compliance")
def auditor_compliance(user:User=Depends(require_roles("Auditor")),db:Session=Depends(get_db)):
    users=db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id)).all()
    documents=db.scalars(select(StaffDocument).where(StaffDocument.tenant_id==user.tenant_id)).all()
    leave=db.scalars(select(TeacherLeaveRequest).where(TeacherLeaveRequest.tenant_id==user.tenant_id)).all()
    audits=db.scalars(select(Audit).where(Audit.tenant_id==user.tenant_id)).all()
    checks=[
      {"key":"active_users","control":"Active user accounts","status":"PASS" if all(x.is_active for x in users) else "REVIEW","value":f"{sum(x.is_active for x in users)}/{len(users)} active","detail":"Review inactive accounts and confirm they should remain disabled."},
      {"key":"open_grievances","control":"Open grievance oversight","status":"PASS" if not any(x.status in {"Open","In Progress"} for x in grievances) else "REVIEW","value":f"{sum(x.status in {'Open','In Progress'} for x in grievances)} open","detail":"Open or in-progress grievances require operational follow-up."},
      {"key":"staff_documents","control":"Staff document status","status":"PASS" if not any(x.status in {"PENDING","EXPIRED"} for x in documents) else "REVIEW","value":f"{sum(x.status in {'PENDING','EXPIRED'} for x in documents)} pending/expired","detail":"Pending or expired staff records require HR review."},
      {"key":"leave_requests","control":"Pending staff leave","status":"PASS" if not any(x.status=="PENDING" for x in leave) else "REVIEW","value":f"{sum(x.status=='PENDING' for x in leave)} pending","detail":"Pending teacher leave requests require authorized review."},
      {"key":"audit_events","control":"Audit trail availability","status":"PASS" if audits else "REVIEW","value":f"{len(audits)} events","detail":"Audit events provide evidence of privileged and operational actions."},
    ]
    return {"summary":{"total":len(checks),"pass":sum(x["status"]=="PASS" for x in checks),"review":sum(x["status"]=="REVIEW" for x in checks)},"checks":checks}

@app.get("/api/v1/auditor/exceptions")
def auditor_exceptions(user:User=Depends(require_roles("Auditor")),db:Session=Depends(get_db)):
    items=[]
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id)).all()
    for x in grievances:
        if x.status in {"Open","In Progress"} and x.priority in {"High","Urgent"}:
            items.append({"type":"GRIEVANCE","severity":"HIGH" if x.priority=="Urgent" else "MEDIUM","reference":x.ticket_no,"title":x.subject,"status":x.status,"detail":f"{x.priority} priority grievance remains unresolved.","created_at":x.created_at})
    documents=db.scalars(select(StaffDocument).where(StaffDocument.tenant_id==user.tenant_id)).all()
    for x in documents:
        if x.status in {"PENDING","EXPIRED"}:
            items.append({"type":"STAFF_DOCUMENT","severity":"HIGH" if x.status=="EXPIRED" else "MEDIUM","reference":str(x.id),"title":x.title,"status":x.status,"detail":f"{x.document_type} requires HR review.","created_at":x.created_at})
    leave=db.scalars(select(TeacherLeaveRequest).where(TeacherLeaveRequest.tenant_id==user.tenant_id,TeacherLeaveRequest.status=="PENDING")).all()
    for x in leave:
        items.append({"type":"LEAVE","severity":"LOW","reference":str(x.id),"title":x.leave_type,"status":x.status,"detail":"Teacher leave request is awaiting authorized review.","created_at":x.created_at})
    inventory=db.scalars(select(CampusInventoryItem).where(CampusInventoryItem.tenant_id==user.tenant_id)).all()
    for x in inventory:
        if x.quantity<=x.minimum_quantity:
            items.append({"type":"INVENTORY","severity":"MEDIUM","reference":str(x.id),"title":x.name,"status":"LOW_STOCK","detail":f"Quantity {x.quantity} is at or below minimum {x.minimum_quantity}.","created_at":x.updated_at})
    assets=db.scalars(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id)).all()
    for x in assets:
        if x.condition in {"DAMAGED","REPAIR"}:
            items.append({"type":"ASSET","severity":"HIGH" if x.condition=="DAMAGED" else "MEDIUM","reference":x.asset_code,"title":x.name,"status":x.condition,"detail":"Asset condition requires operational attention.","created_at":x.updated_at})
    rank={"HIGH":0,"MEDIUM":1,"LOW":2}
    items.sort(key=lambda x:(rank.get(x["severity"],9),-(x["created_at"].timestamp() if x["created_at"] else 0)))
    return {"summary":{"total":len(items),"high":sum(x["severity"]=="HIGH" for x in items),"medium":sum(x["severity"]=="MEDIUM" for x in items),"low":sum(x["severity"]=="LOW" for x in items)},"exceptions":items[:200]}

@app.get("/api/v1/auditor/evidence")
def auditor_evidence(user:User=Depends(require_roles("Auditor")),db:Session=Depends(get_db)):
    items=[]
    documents=db.scalars(select(StaffDocument).where(StaffDocument.tenant_id==user.tenant_id).order_by(StaffDocument.id.desc())).all()
    for x in documents:
        staff=db.get(User,x.staff_user_id)
        if not staff or staff.tenant_id!=user.tenant_id: continue
        items.append({"id":f"STAFF_DOCUMENT-{x.id}","module":"HR","evidence_type":"Staff Document","reference":str(x.id),"title":x.title,"owner":staff.name,"status":"AVAILABLE" if x.document_ref else "MISSING","source_status":x.status,"evidence_ref":x.document_ref or "","created_at":x.updated_at,"detail":f"{x.document_type} • {x.status}"})
    payments=db.scalars(select(FeePayment).where(FeePayment.tenant_id==user.tenant_id).order_by(FeePayment.id.desc())).all()
    for x in payments:
        student=db.get(User,x.student_user_id)
        if not student or student.tenant_id!=user.tenant_id: continue
        items.append({"id":f"PAYMENT-{x.id}","module":"Finance","evidence_type":"Payment Receipt","reference":x.receipt_no,"title":f"Receipt {x.receipt_no}","owner":student.name,"status":"AVAILABLE","source_status":"RECORDED","evidence_ref":x.reference or x.receipt_no,"created_at":x.paid_at,"detail":f"Payment ledger #{x.ledger_id}"})
    reconciliations=db.scalars(select(FinanceReconciliation).where(FinanceReconciliation.tenant_id==user.tenant_id).order_by(FinanceReconciliation.id.desc())).all()
    for x in reconciliations:
        items.append({"id":f"RECONCILIATION-{x.id}","module":"Finance","evidence_type":"Reconciliation","reference":x.reference or str(x.id),"title":f"Reconciliation {x.reconciliation_date.date().isoformat()}","owner":f"User #{x.recorded_by}","status":"AVAILABLE" if x.reference else "MISSING","source_status":x.status,"evidence_ref":x.reference or "","created_at":x.created_at,"detail":f"Difference: {x.difference}"})
    history=db.scalars(select(EnrollmentHistory).where(EnrollmentHistory.tenant_id==user.tenant_id).order_by(EnrollmentHistory.id.desc())).all()
    for x in history:
        student=db.get(User,x.student_user_id)
        if not student or student.tenant_id!=user.tenant_id: continue
        items.append({"id":f"ENROLLMENT-{x.id}","module":"Admissions","evidence_type":"Enrollment History","reference":str(x.id),"title":x.event_type.replace("_"," ").title(),"owner":student.name,"status":"AVAILABLE","source_status":"RECORDED","evidence_ref":f"enrollment_history:{x.id}","created_at":x.created_at,"detail":x.details or "Recorded enrollment lifecycle event"})
    audits=db.scalars(select(Audit).where(Audit.tenant_id==user.tenant_id).order_by(Audit.id.desc()).limit(100)).all()
    for x in audits:
        items.append({"id":f"AUDIT-{x.id}","module":"Audit","evidence_type":"Audit Event","reference":str(x.id),"title":f"{x.action} • {x.resource}","owner":x.actor,"status":"AVAILABLE","source_status":"RECORDED","evidence_ref":f"audit_event:{x.id}","created_at":x.created_at,"detail":x.details or "System audit event"})
    items.sort(key=lambda x:-(x["created_at"].timestamp() if x["created_at"] else 0))
    return {"summary":{"total":len(items),"available":sum(x["status"]=="AVAILABLE" for x in items),"missing":sum(x["status"]=="MISSING" for x in items),"modules":len(set(x["module"] for x in items))},"evidence":items[:300]}

@app.get("/api/v1/auditor/export-reports")
def auditor_export_reports(user:User=Depends(require_roles("Auditor")),db:Session=Depends(get_db)):
    audits=db.scalars(select(Audit).where(Audit.tenant_id==user.tenant_id).order_by(Audit.id.desc())).all()
    users=db.scalars(select(User).where(User.tenant_id==user.tenant_id)).all()
    grievances=db.scalars(select(Grievance).where(Grievance.tenant_id==user.tenant_id)).all()
    documents=db.scalars(select(StaffDocument).where(StaffDocument.tenant_id==user.tenant_id)).all()
    payments=db.scalars(select(FeePayment).where(FeePayment.tenant_id==user.tenant_id)).all()
    reconciliations=db.scalars(select(FinanceReconciliation).where(FinanceReconciliation.tenant_id==user.tenant_id)).all()
    inventory=db.scalars(select(CampusInventoryItem).where(CampusInventoryItem.tenant_id==user.tenant_id)).all()
    assets=db.scalars(select(CampusAsset).where(CampusAsset.tenant_id==user.tenant_id)).all()
    open_grievances=sum(x.status in {"Open","In Progress"} for x in grievances)
    document_issues=sum(x.status in {"PENDING","EXPIRED"} for x in documents)
    low_stock=sum(x.quantity<=x.minimum_quantity for x in inventory)
    asset_issues=sum(x.condition in {"DAMAGED","REPAIR"} for x in assets)
    generated_at=dt.datetime.utcnow()
    reports=[
      {"key":"audit_trail","name":"Audit Trail Report","category":"Audit","description":"Privileged and operational activity recorded for this institution.","records":len(audits),"status":"READY","generated_at":generated_at},
      {"key":"compliance","name":"Compliance Summary","category":"Compliance","description":"Current account, grievance, HR-document and audit-control review summary.","records":5,"status":"READY","generated_at":generated_at},
      {"key":"exceptions","name":"Exception Report","category":"Exceptions","description":"Open operational exceptions requiring authorized follow-up.","records":open_grievances+document_issues+low_stock+asset_issues,"status":"READY","generated_at":generated_at},
      {"key":"evidence","name":"Evidence Register","category":"Evidence","description":"Evidence references across HR, finance, admissions and audit records.","records":len(documents)+len(payments)+len(reconciliations)+len(audits),"status":"READY","generated_at":generated_at},
      {"key":"user_access","name":"User Access Report","category":"Access","description":"Institution user-account population and active access state.","records":len(users),"status":"READY","generated_at":generated_at},
    ]
    return {"summary":{"reports":len(reports),"ready":sum(x["status"]=="READY" for x in reports),"audit_events":len(audits),"exceptions":open_grievances+document_issues+low_stock+asset_issues},"reports":reports}

@app.get("/api/v1/audit")
def audits(
    user:User=Depends(require_roles("Institution Admin","Campus Admin","Auditor")),
    db:Session=Depends(get_db),
):
    rows=db.scalars(
        select(Audit)
        .where(Audit.tenant_id==user.tenant_id)
        .order_by(Audit.id.desc()).limit(200)
    ).all()
    return [
        {"id":a.id,"actor":a.actor,"action":a.action,"resource":a.resource,
         "details":a.details,"created_at":a.created_at}
        for a in rows
    ]

@app.post("/api/v1/module-actions/{action}")
def module_action(
    action: str,
    payload: dict,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    page = str(payload.get("page", "")).strip()
    if not page:
        raise HTTPException(400, "page is required")
    allowed_actions = {
        "approve",
        "pay",
        "message",
        "create_grievance",
        "request_leave",
        "export",
        "manage_users",
    }
    if action not in allowed_actions:
        raise HTTPException(400, "Unsupported module action")
    if not can(user.role, page, action):
        raise HTTPException(403, "You do not have permission for this action")
    details = str(payload.get("details", "")).strip()
    audit(db, user, action.upper(), page, details)
    db.commit()
    return {
        "ok": True,
        "page": page,
        "action": action,
        "message": f"{action.replace('_', ' ').title()} action accepted.",
    }

@app.post("/api/v1/ai/chat")
def ai_chat(payload:AIChatRequest,user:User=Depends(current_user)):
    return {
        "answer":"AI provider adapter is ready. Connect the approved production model/provider and filter retrieved institutional context by role and tenant.",
        "question":payload.message,
        "requires_provider":True,
        "role":user.role,
        "tenant_id":user.tenant_id,
    }
