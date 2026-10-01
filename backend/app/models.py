import datetime as dt
from sqlalchemy import String, Text, DateTime, Float, Numeric, Boolean, ForeignKey, UniqueConstraint, Integer
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def utcnow():
    return dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)

class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    institution_type: Mapped[str] = mapped_column(String(30), default="UNIVERSITY", index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(80), index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    tenant_id: Mapped[int] = mapped_column(default=1, index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class StaffAttendance(Base):
    __tablename__ = "staff_attendance"
    __table_args__ = (UniqueConstraint("tenant_id","staff_user_id","attendance_date", name="uq_staff_attendance_day"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attendance_date: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(30), default="PRESENT")
    note: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class StaffDocument(Base):
    __tablename__ = "staff_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    document_type: Mapped[str] = mapped_column(String(80), index=True)
    title: Mapped[str] = mapped_column(String(180))
    document_ref: Mapped[str] = mapped_column(String(500), default="")
    expiry_date: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class RecruitmentCandidate(Base):
    __tablename__ = "recruitment_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[str] = mapped_column(String(180), index=True)
    phone: Mapped[str] = mapped_column(String(40), default="")
    position: Mapped[str] = mapped_column(String(120), index=True)
    stage: Mapped[str] = mapped_column(String(40), default="APPLIED", index=True)
    source: Mapped[str] = mapped_column(String(80), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class StaffPerformanceReview(Base):
    __tablename__ = "staff_performance_reviews"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    staff_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    review_period: Mapped[str] = mapped_column(String(80), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    strengths: Mapped[str] = mapped_column(Text, default="")
    improvement_areas: Mapped[str] = mapped_column(Text, default="")
    goals: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED")
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"
    __table_args__ = (UniqueConstraint("parent_user_id","student_user_id", name="uq_parent_student"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    parent_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    relationship: Mapped[str] = mapped_column(String(40), default="Guardian")
    tenant_id: Mapped[int] = mapped_column(index=True)

class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    module: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    code: Mapped[str] = mapped_column(String(80), default="")
    category: Mapped[str] = mapped_column(String(80), default="General")
    status: Mapped[str] = mapped_column(String(30), default="Active")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class Grievance(Base):
    __tablename__ = "grievances"
    __table_args__ = (UniqueConstraint("tenant_id","ticket_no", name="uq_grievance_ticket"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ticket_no: Mapped[str] = mapped_column(String(40))
    category: Mapped[str] = mapped_column(String(80), default="General")
    subject: Mapped[str] = mapped_column(String(180))
    details: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="Normal")
    status: Mapped[str] = mapped_column(String(30), default="Open")
    latest_update: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class StudentLeaveRequest(Base):
    __tablename__ = "student_leave_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    requested_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(60), default="Casual")
    start_date: Mapped[dt.datetime] = mapped_column(DateTime)
    end_date: Mapped[dt.datetime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class TeacherLeaveRequest(Base):
    __tablename__ = "teacher_leave_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    leave_type: Mapped[str] = mapped_column(String(60), default="Casual")
    start_date: Mapped[dt.datetime] = mapped_column(DateTime)
    end_date: Mapped[dt.datetime] = mapped_column(DateTime)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="PENDING")
    reviewer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class CommunicationMessage(Base):
    __tablename__ = "communication_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    sender_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recipient_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(180))
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="SENT")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class TeacherNote(Base):
    __tablename__ = "teacher_notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    unit_id: Mapped[int | None] = mapped_column(ForeignKey("academic_units.id"), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(180))
    note: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(30), default="PRIVATE")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

class AcademyEvent(Base):
    __tablename__ = "academy_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int | None] = mapped_column(nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(180))
    event_type: Mapped[str] = mapped_column(String(60), default="General")
    venue: Mapped[str] = mapped_column(String(180), default="")
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime)
    organizer_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    audience_role: Mapped[str] = mapped_column(String(60), default="ALL")
    registration_required: Mapped[bool] = mapped_column(Boolean, default=False)
    registration_deadline: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Published")

class EventRegistration(Base):
    __tablename__ = "event_registrations"
    __table_args__ = (UniqueConstraint("tenant_id","event_id","user_id", name="uq_event_registration_user"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("academy_events.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="Registered")
    registered_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class LibraryBook(Base):
    __tablename__ = "library_books"
    __table_args__ = (UniqueConstraint("tenant_id","accession_no", name="uq_library_book_accession"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    accession_no: Mapped[str] = mapped_column(String(80))
    isbn: Mapped[str | None] = mapped_column(String(30), nullable=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(160), default="")
    category: Mapped[str] = mapped_column(String(100), default="")
    resource_type: Mapped[str] = mapped_column(String(40), default="Book")
    publisher: Mapped[str] = mapped_column(String(160), default="")
    edition: Mapped[str] = mapped_column(String(60), default="")
    publication_year: Mapped[int | None] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(String(60), default="")
    shelf_location: Mapped[str] = mapped_column(String(80), default="")
    academic_unit_id: Mapped[int | None] = mapped_column(ForeignKey("academic_units.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Available")

class LibraryLoan(Base):
    __tablename__ = "library_loans"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("library_books.id"), index=True)
    borrower_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    issued_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    due_at: Mapped[dt.datetime] = mapped_column(DateTime)
    returned_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    fine_amount: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    fine_per_day: Mapped[float] = mapped_column(Numeric(12,2), default=0)
    return_condition: Mapped[str] = mapped_column(String(30), default="")
    fine_status: Mapped[str] = mapped_column(String(30), default="Unpaid")
    status: Mapped[str] = mapped_column(String(30), default="Issued")

class TransportRoute(Base):
    __tablename__ = "transport_routes"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="Active")

class TransportVehicle(Base):
    __tablename__ = "transport_vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    vehicle_number: Mapped[str] = mapped_column(String(60))
    label: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(30), default="Active")

class TransportStop(Base):
    __tablename__ = "transport_stops"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("transport_routes.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    stop_order: Mapped[int] = mapped_column(default=0)

class StudentTransportAllocation(Base):
    __tablename__ = "student_transport_allocations"
    __table_args__ = (UniqueConstraint("tenant_id","student_user_id", name="uq_student_transport_allocation"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("transport_routes.id"), index=True)
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("transport_vehicles.id"), nullable=True, index=True)
    stop_id: Mapped[int] = mapped_column(ForeignKey("transport_stops.id"), index=True)
    pickup_time: Mapped[str] = mapped_column(String(10), default="")
    drop_time: Mapped[str] = mapped_column(String(10), default="")
    status: Mapped[str] = mapped_column(String(30), default="Active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class StudentLocation(Base):
    __tablename__ = "student_locations"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    accuracy: Mapped[float] = mapped_column(Float, default=0)
    source: Mapped[str] = mapped_column(String(30), default="MOBILE")
    tracking_context: Mapped[str] = mapped_column(String(40), default="TRANSPORT")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    recorded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow, index=True)

class SosEvent(Base):
    __tablename__ = "sos_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    actor: Mapped[str] = mapped_column(String(180))
    action: Mapped[str] = mapped_column(String(120))
    resource: Mapped[str] = mapped_column(String(180))
    details: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AcademicUnit(Base):
    __tablename__ = "academic_units"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    campus_id: Mapped[int] = mapped_column(default=1, index=True)
    unit_type: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(180))
    code: Mapped[str] = mapped_column(String(60))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("academic_units.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AcademicAssignment(Base):
    __tablename__ = "academic_assignments"
    __table_args__ = (UniqueConstraint("tenant_id","user_id","unit_id","assignment_type", name="uq_academic_assignment"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("academic_units.id"), index=True)
    assignment_type: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30), default="Active")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class EnrollmentHistory(Base):
    __tablename__ = "enrollment_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(40), index=True)
    from_unit_id: Mapped[int | None] = mapped_column(ForeignKey("academic_units.id"), nullable=True)
    to_unit_id: Mapped[int | None] = mapped_column(ForeignKey("academic_units.id"), nullable=True)
    details: Mapped[str] = mapped_column(Text, default="")
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class AcademicWork(Base):
    __tablename__ = "academic_work"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("academic_units.id"), index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    work_type: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(Text, default="")
    max_marks: Mapped[float] = mapped_column(Float, default=0)
    due_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="PUBLISHED")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class StudentAcademicWork(Base):
    __tablename__ = "student_academic_work"
    __table_args__ = (UniqueConstraint("work_id","student_user_id", name="uq_student_academic_work"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("academic_work.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    submission_text: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    marks: Mapped[float | None] = mapped_column(Float, nullable=True)
    grade: Mapped[str] = mapped_column(String(20), default="")
    feedback: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30), default="PENDING")


class ClassSession(Base):
    __tablename__ = "class_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("academic_units.id"), index=True)
    teacher_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    starts_at: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    ends_at: Mapped[dt.datetime] = mapped_column(DateTime)
    room: Mapped[str] = mapped_column(String(80), default="")
    status: Mapped[str] = mapped_column(String(30), default="SCHEDULED")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class AttendanceEntry(Base):
    __tablename__ = "attendance_entries"
    __table_args__ = (UniqueConstraint("session_id","student_user_id", name="uq_session_student_attendance"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_sessions.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="PRESENT")
    note: Mapped[str] = mapped_column(Text, default="")
    marked_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    marked_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class GradeRule(Base):
    __tablename__ = "grade_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    name: Mapped[str] = mapped_column(String(80))
    min_percentage: Mapped[float] = mapped_column(Float)
    max_percentage: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(20))
    grade_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_status: Mapped[str] = mapped_column(String(30), default="PASS")

class ExamResult(Base):
    __tablename__ = "exam_results"
    __table_args__ = (UniqueConstraint("work_id","student_user_id", name="uq_exam_student_result"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    work_id: Mapped[int] = mapped_column(ForeignKey("academic_work.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    marks: Mapped[float] = mapped_column(Float)
    percentage: Mapped[float] = mapped_column(Float)
    grade: Mapped[str] = mapped_column(String(20))
    grade_point: Mapped[float | None] = mapped_column(Float, nullable=True)
    result_status: Mapped[str] = mapped_column(String(30), default="PASS")
    remarks: Mapped[str] = mapped_column(Text, default="")
    published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class FeeLedger(Base):
    __tablename__ = "fee_ledgers"
    __table_args__ = (UniqueConstraint("tenant_id","student_user_id","fee_code", name="uq_student_fee_code"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    fee_code: Mapped[str] = mapped_column(String(60), index=True)
    title: Mapped[str] = mapped_column(String(180))
    amount_due: Mapped[float] = mapped_column(Numeric(12, 2))
    amount_paid: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    due_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="DUE")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class FeeConcession(Base):
    __tablename__ = "fee_concessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    ledger_id: Mapped[int] = mapped_column(ForeignKey("fee_ledgers.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="APPROVED")
    approved_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class FeeRefund(Base):
    __tablename__ = "fee_refunds"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("fee_payments.id"), index=True)
    ledger_id: Mapped[int] = mapped_column(ForeignKey("fee_ledgers.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    reason: Mapped[str] = mapped_column(Text)
    reference: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class FinanceReconciliation(Base):
    __tablename__ = "finance_reconciliations"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    reconciliation_date: Mapped[dt.datetime] = mapped_column(DateTime, index=True)
    expected_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    bank_amount: Mapped[float] = mapped_column(Numeric(12, 2))
    difference: Mapped[float] = mapped_column(Numeric(12, 2))
    reference: Mapped[str] = mapped_column(String(100), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(30))
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class FeePayment(Base):
    __tablename__ = "fee_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(index=True)
    ledger_id: Mapped[int] = mapped_column(ForeignKey("fee_ledgers.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    reference: Mapped[str] = mapped_column(String(100), default="")
    receipt_no: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    paid_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class CampusVisitor(Base):
    __tablename__ = "campus_visitors"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(40), default="")
    purpose: Mapped[str] = mapped_column(String(250))
    person_to_meet: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(30), default="CHECKED_IN", index=True)
    checked_in_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    checked_out_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class CampusInventoryItem(Base):
    __tablename__ = "campus_inventory_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), default="General", index=True)
    item_code: Mapped[str] = mapped_column(String(60), default="")
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    minimum_quantity: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[str] = mapped_column(String(120), default="")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class CampusAsset(Base):
    __tablename__ = "campus_assets"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    asset_code: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(80), default="General", index=True)
    serial_number: Mapped[str] = mapped_column(String(120), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    assigned_to: Mapped[str] = mapped_column(String(120), default="")
    condition: Mapped[str] = mapped_column(String(30), default="GOOD")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class Hostel(Base):
    __tablename__ = "hostels"
    __table_args__ = (UniqueConstraint("tenant_id","campus_id","code", name="uq_hostel_code"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    name: Mapped[str] = mapped_column(String(160))
    code: Mapped[str] = mapped_column(String(60))
    hostel_type: Mapped[str] = mapped_column(String(30), default="GENERAL")
    warden_name: Mapped[str] = mapped_column(String(120), default="")
    warden_phone: Mapped[str] = mapped_column(String(40), default="")
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class HostelRoom(Base):
    __tablename__ = "hostel_rooms"
    __table_args__ = (UniqueConstraint("tenant_id","hostel_id","room_number", name="uq_hostel_room"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    room_number: Mapped[str] = mapped_column(String(40))
    floor: Mapped[str] = mapped_column(String(40), default="")
    capacity: Mapped[int] = mapped_column(Integer, default=1)
    room_type: Mapped[str] = mapped_column(String(60), default="STANDARD")
    status: Mapped[str] = mapped_column(String(30), default="AVAILABLE")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class HostelAllocation(Base):
    __tablename__ = "hostel_allocations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    hostel_id: Mapped[int] = mapped_column(ForeignKey("hostels.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("hostel_rooms.id"), index=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    bed_number: Mapped[str] = mapped_column(String(40), default="")
    check_in_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    check_out_at: Mapped[dt.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    notes: Mapped[str] = mapped_column(Text, default="")
    allocated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)


class HealthRecord(Base):
    __tablename__ = "health_records"
    __table_args__ = (UniqueConstraint("tenant_id","person_user_id", name="uq_health_record_person"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    person_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    blood_group: Mapped[str] = mapped_column(String(10), default="")
    allergies: Mapped[str] = mapped_column(Text, default="")
    medical_conditions: Mapped[str] = mapped_column(Text, default="")
    emergency_contact_name: Mapped[str] = mapped_column(String(120), default="")
    emergency_contact_phone: Mapped[str] = mapped_column(String(40), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)

class HealthVisit(Base):
    __tablename__ = "health_visits"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(Integer, index=True)
    campus_id: Mapped[int] = mapped_column(Integer, index=True)
    person_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    visit_type: Mapped[str] = mapped_column(String(40), default="GENERAL")
    complaint: Mapped[str] = mapped_column(Text)
    action_taken: Mapped[str] = mapped_column(Text, default="")
    disposition: Mapped[str] = mapped_column(String(40), default="RETURNED")
    visited_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
    recorded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=utcnow)
