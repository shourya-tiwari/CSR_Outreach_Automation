"""Company search, profile, and status/notes endpoints."""

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db
from ..scoring import compute_lead_score

router = APIRouter(prefix="/api/companies", tags=["companies"])

_CSV_COLUMNS = [
    "name",
    "industry",
    "city",
    "state",
    "website",
    "csr_focus",
    "csr_spending",
    "revenue",
    "employee_count",
    "status",
    "last_contacted_date",
    "follow_up_date",
    "lead_score",
    "priority",
]


def _get_company_or_404(db: Session, company_id: int) -> models.Company:
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def _to_detail(company: models.Company) -> schemas.CompanyDetail:
    detail = schemas.CompanyDetail.model_validate(company)
    detail.lead_score = schemas.LeadScore(**compute_lead_score(company))
    return detail


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
            {**c.__dict__, "contact_count": len(c.contacts), "lead_score": compute_lead_score(c)}
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
    return _to_detail(crud.create_company(db, payload))


@router.get("/export")
def export_companies(
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
    db: Session = Depends(get_db),
):
    """CSV export, respecting the same filters as GET /api/companies (no
    skip/limit - export always covers the full filtered result set).
    """
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
        skip=0,
        limit=1_000_000,
    )

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=_CSV_COLUMNS)
    writer.writeheader()
    for company in companies:
        score = compute_lead_score(company)
        writer.writerow(
            {
                "name": company.name,
                "industry": company.industry or "",
                "city": company.city or "",
                "state": company.state or "",
                "website": company.website or "",
                "csr_focus": company.csr_focus or "",
                "csr_spending": company.csr_spending if company.csr_spending is not None else "",
                "revenue": company.revenue if company.revenue is not None else "",
                "employee_count": company.employee_count if company.employee_count is not None else "",
                "status": company.status.value,
                "last_contacted_date": company.last_contacted_date or "",
                "follow_up_date": company.follow_up_date or "",
                "lead_score": score["score"],
                "priority": score["priority"],
            }
        )

    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=companies.csv"},
    )


@router.post("/import", response_model=schemas.ImportResult)
async def import_companies(file: UploadFile, db: Session = Depends(get_db)):
    """CSV import: one company per row, columns matching CompanyCreate
    field names (see _CSV_COLUMNS / the export format above). Rows with a
    duplicate name/website are skipped (not overwritten) rather than
    erroring the whole upload - same "review, don't silently clobber"
    principle as the single-company duplicate-detection flow.
    """
    raw = (await file.read()).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(raw))
    result = crud.import_companies_from_rows(db, list(reader))
    return schemas.ImportResult(**result)


@router.get("/{company_id}", response_model=schemas.CompanyDetail)
def get_company(company_id: int, db: Session = Depends(get_db)):
    return _to_detail(_get_company_or_404(db, company_id))


@router.patch("/{company_id}", response_model=schemas.CompanyDetail)
def update_company(company_id: int, payload: schemas.CompanyUpdate, db: Session = Depends(get_db)):
    company = _get_company_or_404(db, company_id)
    return _to_detail(crud.update_company(db, company, payload))


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
