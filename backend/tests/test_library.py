import os
os.environ["DATABASE_URL"]="sqlite:///./test_library.db"

import datetime as dt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.database import Base,engine,SessionLocal
from app.models import Institution,Campus,User,AcademicUnit,LibraryBook,LibraryLoan
from app.security import hash_password

client=TestClient(app); PASSWORD="Test@123"

@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine); Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        db.add(Institution(id=1,name="Library School",institution_type="SCHOOL",code="LIB")); db.flush()
        db.add(Campus(id=1,tenant_id=1,name="Main Campus",code="MAIN")); db.flush()
        db.add_all([
            User(id=1,email="admin@lib.local",name="Admin",role="Institution Admin",password_hash=hash_password(PASSWORD),tenant_id=1,campus_id=1,is_active=True),
            User(id=2,email="student@lib.local",name="Student",role="Student",password_hash=hash_password(PASSWORD),tenant_id=1,campus_id=1,is_active=True),
            User(id=3,email="teacher@lib.local",name="Teacher",role="Teacher",password_hash=hash_password(PASSWORD),tenant_id=1,campus_id=1,is_active=True),
        ]); db.add(AcademicUnit(id=1,tenant_id=1,campus_id=1,unit_type="COURSE",name="Mathematics",code="MATH",status="Active")); db.commit()
    yield
    Base.metadata.drop_all(bind=engine)

def auth(email):
    r=client.post("/api/v1/auth/login",json={"email":email,"password":PASSWORD}); assert r.status_code==200
    return {"Authorization":"Bearer "+r.json()["access_token"]}

def add_book(h,accession="ACC-1"):
    return client.post("/api/v1/admin/library/books",headers=h,json={"campus_id":1,"accession_no":accession,"isbn":"978000000001","title":"Test Book","author":"GAINT","category":"Mathematics","resource_type":"Textbook","publisher":"GAINT Press","edition":"1","publication_year":2026,"language":"English","shelf_location":"A-1","academic_unit_id":1})

def test_catalogue_extended_fields_and_self_service():
    admin=auth("admin@lib.local"); r=add_book(admin); assert r.status_code==200,r.text
    d=client.get("/api/v1/admin/library",headers=admin); assert d.status_code==200
    b=d.json()["books"][0]; assert b["resource_type"]=="Textbook"; assert b["academic_unit_name"]=="Mathematics"; assert b["shelf_location"]=="A-1"
    for email in ("student@lib.local","teacher@lib.local"):
        me=client.get("/api/v1/library/me",headers=auth(email)); assert me.status_code==200
        assert me.json()["catalogue"][0]["title"]=="Test Book"

def test_library_admin_endpoints_reject_non_admin():
    student=auth("student@lib.local")
    assert client.get("/api/v1/admin/library",headers=student).status_code==403
    assert add_book(student,"BLOCKED").status_code==403

def test_double_issue_and_borrower_validation():
    admin=auth("admin@lib.local"); book=add_book(admin).json()
    due=(dt.datetime.utcnow()+dt.timedelta(days=7)).strftime("%Y-%m-%dT23:59:00")
    first=client.post("/api/v1/admin/library/loans",headers=admin,json={"book_id":book["id"],"borrower_user_id":2,"due_at":due,"fine_per_day":5}); assert first.status_code==200,first.text
    duplicate=client.post("/api/v1/admin/library/loans",headers=admin,json={"book_id":book["id"],"borrower_user_id":3,"due_at":due,"fine_per_day":5}); assert duplicate.status_code==409
    bad=client.post("/api/v1/admin/library/loans",headers=admin,json={"book_id":book["id"],"borrower_user_id":1,"due_at":due,"fine_per_day":5}); assert bad.status_code in (400,409)

def test_return_calculates_overdue_fine_and_damaged_status():
    admin=auth("admin@lib.local"); book=add_book(admin).json()
    with SessionLocal() as db:
        loan=LibraryLoan(tenant_id=1,campus_id=1,book_id=book["id"],borrower_user_id=2,due_at=dt.datetime.utcnow()-dt.timedelta(days=3),fine_per_day=5,status="Issued")
        db.add(loan); b=db.get(LibraryBook,book["id"]); b.status="Issued"; db.commit(); loan_id=loan.id
    r=client.patch(f"/api/v1/admin/library/loans/{loan_id}/return",headers=admin,json={"fine_amount":0,"return_condition":"Damaged","fine_status":"Unpaid"}); assert r.status_code==200,r.text
    with SessionLocal() as db:
        loan=db.get(LibraryLoan,loan_id); b=db.get(LibraryBook,book["id"])
        assert float(loan.fine_amount)>=15; assert loan.return_condition=="Damaged"; assert b.status=="Damaged"

def test_self_service_is_read_only_and_scoped():
    student=auth("student@lib.local"); teacher=auth("teacher@lib.local")
    assert client.get("/api/v1/library/me",headers=student).status_code==200
    assert client.get("/api/v1/library/me",headers=teacher).status_code==200
    assert client.post("/api/v1/admin/library/books",headers=teacher,json={}).status_code==403
