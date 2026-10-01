"""extend library catalogue and circulation metadata

Revision ID: 20261001_01
Revises: 20260930_21
"""
from alembic import op
import sqlalchemy as sa

revision="20261001_01"
down_revision="20260930_21"
branch_labels=None
depends_on=None

def upgrade():
    for name,typ,default in [
        ("resource_type",sa.String(40),"Book"),("publisher",sa.String(160),""),
        ("edition",sa.String(60),""),("language",sa.String(60),""),
        ("shelf_location",sa.String(80),"")]:
        op.add_column("library_books",sa.Column(name,typ,nullable=False,server_default=default))
    op.add_column("library_books",sa.Column("publication_year",sa.Integer(),nullable=True))
    op.add_column("library_books",sa.Column("academic_unit_id",sa.Integer(),sa.ForeignKey("academic_units.id"),nullable=True))
    op.create_index("ix_library_books_academic_unit_id","library_books",["academic_unit_id"])
    op.add_column("library_loans",sa.Column("fine_per_day",sa.Numeric(12,2),nullable=False,server_default="0"))
    op.add_column("library_loans",sa.Column("return_condition",sa.String(30),nullable=False,server_default=""))
    op.add_column("library_loans",sa.Column("fine_status",sa.String(30),nullable=False,server_default="Unpaid"))

def downgrade():
    for name in ("fine_status","return_condition","fine_per_day"): op.drop_column("library_loans",name)
    op.drop_index("ix_library_books_academic_unit_id",table_name="library_books")
    for name in ("academic_unit_id","publication_year","shelf_location","language","edition","publisher","resource_type"):
        op.drop_column("library_books",name)
