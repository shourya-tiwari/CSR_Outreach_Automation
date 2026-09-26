"""Proposal update/delete, addressed by the proposal's own id (Phase 5).
Creation lives in routers/companies.py (POST /{company_id}/proposals),
matching the contacts/notes sub-resource pattern.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/proposals", tags=["proposals"])


@router.patch("/{proposal_id}", response_model=schemas.ProposalOut)
def update_proposal(proposal_id: int, payload: schemas.ProposalUpdate, db: Session = Depends(get_db)):
    proposal = crud.get_proposal(db, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return crud.update_proposal(db, proposal, payload)


@router.delete("/{proposal_id}", status_code=204)
def delete_proposal(proposal_id: int, db: Session = Depends(get_db)):
    proposal = crud.get_proposal(db, proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Proposal not found")
    crud.delete_proposal(db, proposal)
