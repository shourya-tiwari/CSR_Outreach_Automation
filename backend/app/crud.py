"""Data-access functions (CRUD) for companies, contacts, and notes."""

import re
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from . import models, schemas


def _normalize_domain(website: str) -> str:
    if not website:
        return ""
    normalized = website.strip().lower()
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = re.sub(r"^www\.", "", normalized)
    return normalized.rstrip("/")


# ----------------------------------------------------------------------------
# Companies
# ----------------------------------------------------------------------------
def find_duplicate_company(
    db: Session, name: str, website: Optional[str]
) -> Optional[models.Company]:
    """Best-effort duplicate check by case-insensitive name or website match.

    Fine at this tool's scale (a single NGO's outreach list, not a
    bulk data warehouse) - see docs/PROJECT_OVERVIEW.md's "keep
    infrastructure simple" principle.
    """
    name_match = (
        db.query(models.Company).filter(models.Company.name.ilike(name.strip())).first()
    )
    if name_match:
        return name_match

    target_domain = _normalize_domain(website) if website else ""
    if target_domain:
        for company in db.query(models.Company).filter(models.Company.website.isnot(None)).all():
            if _normalize_domain(company.website) == target_domain:
                return company
    return None


def create_company(db: Session, payload: schemas.CompanyCreate) -> models.Company:
    company = models.Company(**payload.model_dump())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def get_company(db: Session, company_id: int) -> Optional[models.Company]:
    return (
        db.query(models.Company)
        .options(joinedload(models.Company.contacts), joinedload(models.Company.notes))
        .filter(models.Company.id == company_id)
        .first()
    )


def search_companies(
    db: Session,
    *,
    name: Optional[str] = None,
    industry: Optional[str] = None,
    state: Optional[str] = None,
    city: Optional[str] = None,
    csr_focus: Optional[str] = None,
    status: Optional[models.LeadStatus] = None,
    min_csr_spending: Optional[float] = None,
    max_csr_spending: Optional[float] = None,
    min_revenue: Optional[float] = None,
    max_revenue: Optional[float] = None,
    min_employees: Optional[int] = None,
    max_employees: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[models.Company]:
    query = db.query(models.Company)

    if name:
        query = query.filter(models.Company.name.ilike(f"%{name}%"))
    if industry:
        query = query.filter(models.Company.industry.ilike(f"%{industry}%"))
    if state:
        query = query.filter(models.Company.state.ilike(f"%{state}%"))
    if city:
        query = query.filter(models.Company.city.ilike(f"%{city}%"))
    if csr_focus:
        query = query.filter(models.Company.csr_focus.ilike(f"%{csr_focus}%"))
    if status:
        query = query.filter(models.Company.status == status)
    if min_csr_spending is not None:
        query = query.filter(models.Company.csr_spending >= min_csr_spending)
    if max_csr_spending is not None:
        query = query.filter(models.Company.csr_spending <= max_csr_spending)
    if min_revenue is not None:
        query = query.filter(models.Company.revenue >= min_revenue)
    if max_revenue is not None:
        query = query.filter(models.Company.revenue <= max_revenue)
    if min_employees is not None:
        query = query.filter(models.Company.employee_count >= min_employees)
    if max_employees is not None:
        query = query.filter(models.Company.employee_count <= max_employees)

    return (
        query.options(joinedload(models.Company.contacts))
        .order_by(models.Company.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_company(
    db: Session, company: models.Company, payload: schemas.CompanyUpdate
) -> models.Company:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    db.commit()
    db.refresh(company)
    return company


def delete_company(db: Session, company: models.Company) -> None:
    db.delete(company)
    db.commit()


# ----------------------------------------------------------------------------
# Contacts
# ----------------------------------------------------------------------------
def create_contact(
    db: Session, company_id: int, payload: schemas.ContactCreate
) -> models.Contact:
    contact = models.Contact(company_id=company_id, **payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


def get_contact(db: Session, contact_id: int) -> Optional[models.Contact]:
    return db.query(models.Contact).filter(models.Contact.id == contact_id).first()


def update_contact(
    db: Session, contact: models.Contact, payload: schemas.ContactUpdate
) -> models.Contact:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)
    db.commit()
    db.refresh(contact)
    return contact


def delete_contact(db: Session, contact: models.Contact) -> None:
    db.delete(contact)
    db.commit()


# ----------------------------------------------------------------------------
# Notes
# ----------------------------------------------------------------------------
def create_note(db: Session, company_id: int, payload: schemas.NoteCreate) -> models.Note:
    note = models.Note(company_id=company_id, body=payload.body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def get_note(db: Session, note_id: int) -> Optional[models.Note]:
    return db.query(models.Note).filter(models.Note.id == note_id).first()


def delete_note(db: Session, note: models.Note) -> None:
    db.delete(note)
    db.commit()
