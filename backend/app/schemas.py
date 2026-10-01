from pydantic import BaseModel, Field
from typing import Optional

class LoginRequest(BaseModel):
    email: str
    password: str

class RecordIn(BaseModel):
    module: str
    name: str
    code: str = ""
    category: str = "General"
    status: str = "Active"
    notes: str = ""

class LocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float = Field(default=0, ge=0)
    source: str = "MOBILE"
    tracking_context: str = "TRANSPORT"
    status: str = "ACTIVE"

class SosIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    message: str = ""

class AIChatRequest(BaseModel):
    message: str


class InstitutionIn(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    institution_type: str
    code: str = Field(min_length=2, max_length=50)


class AcademicUnitIn(BaseModel):
    unit_type: str
    name: str = Field(min_length=2, max_length=180)
    code: str = Field(min_length=1, max_length=60)
    parent_id: Optional[int] = None
    campus_id: int = 1
    status: str = "Active"


class AcademicAssignmentIn(BaseModel):
    user_id: int
    unit_id: int
    assignment_type: str
    status: str = "Active"


class AcademicActivityIn(BaseModel):
    module: str
    unit_id: int
    name: str = Field(min_length=2, max_length=180)
    code: str = ""
    category: str = "General"
    status: str = "Active"
    notes: str = ""


class AcademicWorkIn(BaseModel):
    unit_id: int
    work_type: str
    title: str = Field(min_length=2, max_length=180)
    description: str = ""
    max_marks: float = Field(default=0, ge=0)
    due_at: Optional[str] = None

class AcademicWorkUpdateIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = ""
    max_marks: float = Field(default=0, ge=0)
    due_at: Optional[str] = None
    status: str = Field(default="PUBLISHED", max_length=30)

class SubmissionIn(BaseModel):
    submission_text: str = Field(min_length=1)

class GradeIn(BaseModel):
    marks: float = Field(ge=0)
    grade: str = ""
    feedback: str = ""


class ClassSessionIn(BaseModel):
    unit_id: int
    title: str = Field(min_length=2, max_length=180)
    starts_at: str
    ends_at: str
    room: str = ""

class ClassSessionUpdateIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    starts_at: str
    ends_at: str
    room: str = ""
    status: str = Field(default="Scheduled", max_length=30)

class AttendanceMarkIn(BaseModel):
    student_user_id: int
    status: str
    note: str = ""


class GradeRuleIn(BaseModel):
    name: str
    min_percentage: float = Field(ge=0, le=100)
    max_percentage: float = Field(ge=0, le=100)
    grade: str
    grade_point: Optional[float] = None
    result_status: str = "PASS"

class ExamResultIn(BaseModel):
    student_user_id: int
    marks: float = Field(ge=0)
    remarks: str = ""


class FeeLedgerIn(BaseModel):
    student_user_id: int
    fee_code: str = Field(min_length=1, max_length=60)
    title: str = Field(min_length=2, max_length=180)
    amount_due: float = Field(gt=0)
    due_at: Optional[str] = None

class FeeLedgerUpdateIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    amount_due: float = Field(gt=0)
    due_at: Optional[str] = None


class FeeConcessionIn(BaseModel):
    ledger_id: int = Field(ge=1)
    amount: float = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)

class FeeRefundIn(BaseModel):
    payment_id: int = Field(ge=1)
    amount: float = Field(gt=0)
    reason: str = Field(min_length=2, max_length=1000)
    reference: str = Field(default="", max_length=100)

class FinanceReconciliationIn(BaseModel):
    reconciliation_date: str
    bank_amount: float = Field(ge=0)
    reference: str = Field(default="", max_length=100)
    notes: str = Field(default="", max_length=1000)

class FeePaymentIn(BaseModel):
    amount: float = Field(gt=0)
    reference: str = Field(default="", max_length=100)


class StaffPerformanceReviewIn(BaseModel):
    staff_user_id: int = Field(ge=1)
    review_period: str = Field(min_length=2, max_length=80)
    rating: int = Field(ge=1, le=5)
    strengths: str = Field(default="", max_length=2000)
    improvement_areas: str = Field(default="", max_length=2000)
    goals: str = Field(default="", max_length=2000)
    status: str = "COMPLETED"

class RecruitmentCandidateIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    phone: str = Field(default="", max_length=40)
    position: str = Field(min_length=2, max_length=120)
    stage: str = "APPLIED"
    source: str = Field(default="", max_length=80)
    notes: str = Field(default="", max_length=1000)

class RecruitmentStageIn(BaseModel):
    stage: str
    notes: Optional[str] = Field(default=None, max_length=1000)

class StaffDocumentIn(BaseModel):
    staff_user_id: int = Field(ge=1)
    document_type: str = Field(min_length=2, max_length=80)
    title: str = Field(min_length=2, max_length=180)
    document_ref: str = Field(default="", max_length=500)
    expiry_date: Optional[str] = None
    status: str = "ACTIVE"
    notes: str = Field(default="", max_length=1000)

class StaffAttendanceIn(BaseModel):
    staff_user_id: int = Field(ge=1)
    attendance_date: str
    status: str
    note: str = Field(default="", max_length=1000)

class UserAdminUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    role: Optional[str] = None
    campus_id: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class UserAdminCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=8, max_length=128)
    role: str
    campus_id: int = Field(default=1, ge=1)


class ParentStudentLinkIn(BaseModel):
    parent_user_id: int
    student_user_id: int
    relationship: str = Field(default="Guardian", min_length=2, max_length=40)


class StudentEnrollmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=180)
    password: str = Field(min_length=8, max_length=128)
    campus_id: int = Field(default=1, ge=1)
    program_unit_id: int
    section_unit_id: Optional[int] = None
    course_unit_ids: list[int] = Field(default_factory=list)
    parent_user_id: Optional[int] = None
    relationship: str = Field(default="Guardian", min_length=2, max_length=40)


class StudentEnrollmentUpdate(BaseModel):
    section_unit_id: Optional[int] = None
    status: Optional[str] = None


class StudentAdminUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=120)
    email: Optional[str] = Field(default=None, min_length=5, max_length=180)
    campus_id: Optional[int] = Field(default=None, ge=1)
    is_active: Optional[bool] = None


class StudentAcademicManagementIn(BaseModel):
    section_unit_id: Optional[int] = None
    course_unit_ids: Optional[list[int]] = None

class StudentGuardianManagementIn(BaseModel):
    parent_user_id: int
    relationship: str = Field(default="Guardian", min_length=2, max_length=40)


class GrievanceIn(BaseModel):
    category: str = "General"
    subject: str
    details: str
    priority: str = "Normal"


class ParentStudentLeaveIn(BaseModel):
    student_user_id: int
    leave_type: str = Field(default="Casual", min_length=2, max_length=60)
    start_date: str
    end_date: str
    reason: str = Field(min_length=2)

class TeacherNoteIn(BaseModel):
    student_user_id: int
    unit_id: Optional[int] = None
    subject: str = Field(min_length=2, max_length=180)
    note: str = Field(min_length=1)
    visibility: str = "PRIVATE"


class TeacherNoteUpdateIn(BaseModel):
    subject: str = Field(min_length=2, max_length=180)
    note: str = Field(min_length=1)
    visibility: str = "PRIVATE"

class TeacherMessageIn(BaseModel):
    recipient_user_id: int
    student_user_id: Optional[int] = None
    subject: str = Field(min_length=2, max_length=180)
    body: str = Field(min_length=1)


class HRLeaveReviewIn(BaseModel):
    status: str
    reviewer_note: str = Field(default="", max_length=1000)

class TeacherLeaveIn(BaseModel):
    leave_type: str = Field(default="Casual", min_length=2, max_length=60)
    start_date: str
    end_date: str
    reason: str = Field(min_length=2)


class CampusVisitorIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(default="", max_length=40)
    purpose: str = Field(min_length=2, max_length=250)
    person_to_meet: str = Field(default="", max_length=120)

class CampusVisitorStatusIn(BaseModel):
    status: str


class CampusInventoryIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(default="General", max_length=80)
    item_code: str = Field(default="", max_length=60)
    quantity: int = Field(default=0, ge=0)
    minimum_quantity: int = Field(default=0, ge=0)
    location: str = Field(default="", max_length=120)
    status: str = "ACTIVE"
    notes: str = Field(default="", max_length=1000)

class CampusInventoryUpdate(BaseModel):
    quantity: int = Field(ge=0)
    status: str = "ACTIVE"
    notes: str = Field(default="", max_length=1000)


class CampusAssetIn(BaseModel):
    asset_code: str = Field(min_length=1, max_length=60)
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(default="General", max_length=80)
    serial_number: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    assigned_to: str = Field(default="", max_length=120)
    condition: str = "GOOD"
    status: str = "ACTIVE"
    notes: str = Field(default="", max_length=1000)

class CampusAssetUpdate(BaseModel):
    location: str = Field(default="", max_length=120)
    assigned_to: str = Field(default="", max_length=120)
    condition: str = "GOOD"
    status: str = "ACTIVE"
    notes: str = Field(default="", max_length=1000)


class CampusEventIn(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    event_type: str = Field(default="General", max_length=60)
    venue: str = Field(default="", max_length=180)
    starts_at: str
    ends_at: str
    audience_role: str = "ALL"
    registration_required: bool = False
    registration_deadline: Optional[str] = None


class CampusGrievanceUpdateIn(BaseModel):
    status: str
    latest_update: str = Field(min_length=2, max_length=2000)


class HostelIn(BaseModel):
    campus_id: int = Field(default=1, ge=1)
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=1, max_length=60)
    hostel_type: str = Field(default="GENERAL", max_length=30)
    warden_name: str = Field(default="", max_length=120)
    warden_phone: str = Field(default="", max_length=40)

class HostelRoomIn(BaseModel):
    hostel_id: int
    room_number: str = Field(min_length=1, max_length=40)
    floor: str = Field(default="", max_length=40)
    capacity: int = Field(default=1, ge=1, le=100)
    room_type: str = Field(default="STANDARD", max_length=60)

class HostelUpdateIn(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    code: str = Field(min_length=1, max_length=60)
    hostel_type: str = Field(default="GENERAL", max_length=30)
    warden_name: str = Field(default="", max_length=120)
    warden_phone: str = Field(default="", max_length=40)
    status: str = Field(default="ACTIVE", max_length=30)

class HostelRoomUpdateIn(BaseModel):
    floor: str = Field(default="", max_length=40)
    capacity: int = Field(default=1, ge=1, le=100)
    room_type: str = Field(default="STANDARD", max_length=60)
    status: str = Field(default="AVAILABLE", max_length=30)


class HostelAllocationIn(BaseModel):
    hostel_id: int
    room_id: int
    student_user_id: int
    bed_number: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=1000)

class HostelCheckoutIn(BaseModel):
    notes: str = Field(default="", max_length=1000)


class HealthRecordIn(BaseModel):
    person_user_id: int
    blood_group: str = Field(default="", max_length=10)
    allergies: str = Field(default="", max_length=2000)
    medical_conditions: str = Field(default="", max_length=2000)
    emergency_contact_name: str = Field(default="", max_length=120)
    emergency_contact_phone: str = Field(default="", max_length=40)
    notes: str = Field(default="", max_length=2000)

class HealthVisitIn(BaseModel):
    person_user_id: int
    visit_type: str = Field(default="GENERAL", max_length=40)
    complaint: str = Field(min_length=1, max_length=2000)
    action_taken: str = Field(default="", max_length=2000)
    disposition: str = Field(default="RETURNED", max_length=40)


class AdminLibraryBookIn(BaseModel):
    campus_id: int = Field(ge=1)
    accession_no: str = Field(min_length=1, max_length=80)
    isbn: str | None = Field(default=None, max_length=30)
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(default="", max_length=160)
    category: str = Field(default="", max_length=100)
    resource_type: str = Field(default="Book", max_length=40)
    publisher: str = Field(default="", max_length=160)
    edition: str = Field(default="", max_length=60)
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    language: str = Field(default="", max_length=60)
    shelf_location: str = Field(default="", max_length=80)
    academic_unit_id: int | None = Field(default=None, ge=1)

class AdminLibraryBookUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(default="", max_length=160)
    category: str = Field(default="", max_length=100)
    isbn: str | None = Field(default=None, max_length=30)
    resource_type: str = Field(default="Book", max_length=40)
    publisher: str = Field(default="", max_length=160)
    edition: str = Field(default="", max_length=60)
    publication_year: int | None = Field(default=None, ge=1000, le=2100)
    language: str = Field(default="", max_length=60)
    shelf_location: str = Field(default="", max_length=80)
    academic_unit_id: int | None = Field(default=None, ge=1)
    status: str = Field(default="Available", max_length=30)


class AdminLibraryLoanIn(BaseModel):
    book_id: int = Field(ge=1)
    borrower_user_id: int = Field(ge=1)
    due_at: str
    fine_per_day: float = Field(default=0, ge=0)

class AdminLibraryReturnIn(BaseModel):
    fine_amount: float = Field(default=0, ge=0)
    return_condition: str = Field(default="Good", max_length=30)
    fine_status: str = Field(default="Unpaid", max_length=30)


class AdminTransportRouteIn(BaseModel):
    campus_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=50)

class AdminTransportVehicleIn(BaseModel):
    campus_id: int = Field(ge=1)
    vehicle_number: str = Field(min_length=1, max_length=60)
    label: str = Field(default="", max_length=120)

class AdminTransportStopIn(BaseModel):
    route_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    stop_order: int = Field(default=0, ge=0)

class AdminTransportAllocationIn(BaseModel):
    student_user_id: int = Field(ge=1)
    route_id: int = Field(ge=1)
    vehicle_id: int | None = Field(default=None, ge=1)
    stop_id: int = Field(ge=1)
    pickup_time: str = Field(default="", max_length=10)
    drop_time: str = Field(default="", max_length=10)
    status: str = Field(default="Active", max_length=30)


class AdminTransportRouteUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=1, max_length=50)
    status: str = Field(min_length=1, max_length=30)

class AdminTransportVehicleUpdate(BaseModel):
    vehicle_number: str = Field(min_length=1, max_length=60)
    label: str = Field(default="", max_length=120)
    status: str = Field(min_length=1, max_length=30)

class AdminTransportStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=30)


class AdminClassSessionIn(BaseModel):
    unit_id: int
    teacher_user_id: int
    title: str = Field(min_length=2, max_length=180)
    starts_at: str
    ends_at: str
    room: str = Field(default="", max_length=120)

class AdminClassSessionUpdate(BaseModel):
    teacher_user_id: int
    title: str = Field(min_length=2, max_length=180)
    starts_at: str
    ends_at: str
    room: str = Field(default="", max_length=120)
    status: str = Field(default="Scheduled", max_length=30)


class AdminInventoryIn(CampusInventoryIn):
    campus_id: int = Field(ge=1)

class AdminAssetIn(CampusAssetIn):
    campus_id: int = Field(ge=1)


class AdminAcademicWorkIn(AcademicWorkIn):
    teacher_user_id: int

class AdminAcademicWorkUpdate(BaseModel):
    teacher_user_id: int
    title: str = Field(min_length=2, max_length=180)
    description: str = ""
    max_marks: float = Field(default=0, ge=0)
    due_at: Optional[str] = None
    status: str = Field(default="PUBLISHED", max_length=30)


class AdminEventUpdateIn(CampusEventIn):
    status: str = Field(default="Published", max_length=30)
