"""Company search, profile, and status/notes endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/companies", tags=["companies"])


def _get_company_or_404(db: Session, company_id: int) -> models.Company:
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("", response_model=list[schemas.CompanyListItem])
def list_companies(
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
    db: Session = Depends(get_db),
):
    companies = crud.search_companies(
        db,
        name=name,
        industry=industry,
        state=state,
        city=city,
        csr_focus=csr_focus,
        status=status,
        min_csr_spending=min_csr_spending,
        max_csr_spending=max_csr_spending,
        min_revenue=min_revenue,
        max_revenue=max_revenue,
        min_employees=min_employees,
        max_employees=max_employees,
        skip=skip,
        limit=limit,
    )
    return [
        schemas.CompanyListItem.model_validate(
            {**c.__dict__, "contact_count": len(c.contacts)}
        )
        for c in companies
    ]


@router.post("", response_model=schemas.CompanyDetail, status_code=201)
def create_company(
    payload: schemas.CompanyCreate, force: bool = False, db: Session = Depends(get_db)
):
    if not force:
        duplicate = crud.find_duplicate_company(db, payload.name, payload.website)
        if duplicate is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "A company with this name or website already exists.",
                    "existing_company_id": duplicate.id,
                    "existing_company_name": duplicate.name,
                },
            )
    return crud.create_company(db, payload)


@router.get("/{company_id}", response_model=schemas.CompanyDetail)
def get_company(company_id: int, db: Session = Depends(get_db)):
    return _get_company_or_404(db, company_id)


@router.patch("/{company_id}", response_model=schemas.CompanyDetail)
def update_company(company_id: int, payload: schemas.CompanyUpdate, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    return crud.update_company(db, company, payload)


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: int, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    crud.delete_company(db, company)


@router.post("/{company_id}/contacts", response_model=schemas.ContactOut, status_code=201)
def add_contact(company_id: int, payload: schemas.ContactCreate, db: Session = Depends(get_db)):
    _get_company_or_404(db, company_id)
    return crud.create_contact(db, company_id, payload)


@router.post("/{company_id}/notes", response_model=schemas.NoteOut, status_code=201)
def add_note(company_id: int, payload: schemas.NoteCreate, db: Session = Depends(get_db)):
    _get_company_or_404(db, company_id)
    return crud.create_note(db, company_id, payload)
