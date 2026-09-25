"""SQLAlchemy models for Phase 1: companies, contacts, notes.

Matches the "Contact Database" data model in docs/PROJECT_OVERVIEW.md:
Company -> Contact(s) -> Outreach status / Notes.
"""

import enum

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class LeadStatus(str, enum.Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    FOLLOW_UP = "Follow-up"
    MEETING = "Meeting"
    PROPOSAL_SENT = "Proposal Sent"
    SUCCESSFUL = "Successful"
    NOT_INTERESTED = "Not Interested"


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    industry = Column(String(120), index=True)
    city = Column(String(120), index=True)
    state = Column(String(120), index=True)
    website = Column(String(500))
    csr_focus = Column(String(255), index=True)
    csr_spending = Column(Float)
    revenue = Column(Float)
    employee_count = Column(Integer)

    status = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    last_contacted_date = Column(Date, nullable=True)
    follow_up_date = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    contacts = relationship(
        "Contact", back_populates="company", cascade="all, delete-orphan", order_by="Contact.id"
    )
    notes = relationship(
        "Note", back_populates="company", cascade="all, delete-orphan", order_by="Note.created_at.desc()"
    )
    activity_logs = relationship(
        "ActivityLog",
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="ActivityLog.created_at.desc()",
    )


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    designation = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    linkedin_url = Column(String(500))
    source_url = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="contacts")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    body = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="notes")


class ActivityLog(Base):
    """Auto-recorded events for Phase 4's recent-activity feed and
    dashboard KPIs (e.g. company added, contact added, status changed).
    Not user-editable - written only by crud.py as a side effect of the
    action it describes.
    """

    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)

    event_type = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    company = relationship("Company", back_populates="activity_logs")
