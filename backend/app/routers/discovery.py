"""CSR decision-maker discovery: website scraping + Hunter/Apollo enrichment."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, enrichment, schemas
from ..database import get_db
from ..scraping import discover_company_contacts

router = APIRouter(prefix="/api/companies", tags=["discovery"])


@router.post("/{company_id}/scrape", response_model=schemas.ScrapeResult)
def scrape_company(company_id: int, db: Session = Depends(get_db)):
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if not company.website:
        raise HTTPException(status_code=400, detail="Company has no website to scan.")

    candidates = discover_company_contacts(company.website)
    return schemas.ScrapeResult(contacts=candidates)


@router.post("/{company_id}/enrich", response_model=schemas.EnrichResult)
def enrich_company(company_id: int, db: Session = Depends(get_db)):
    company = crud.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    if not enrichment.is_configured():
        return schemas.EnrichResult(configured=False, contacts=[])
    if not company.website:
        raise HTTPException(status_code=400, detail="Company has no website to derive a domain from.")

    candidates = enrichment.enrich_company_contacts(company.website)
    return schemas.EnrichResult(configured=True, contacts=candidates)
