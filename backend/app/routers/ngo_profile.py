"""Editable NGO profile (Phase 5) - replaces the env-only NGO_* settings
as the thing NGO staff actually edit. Reused automatically in lead
scoring's location/focus match and in AI-generated content (see
crud.get_ngo_profile / update_ngo_profile for how edits propagate).
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/api/ngo-profile", tags=["ngo-profile"])


@router.get("", response_model=schemas.NGOProfileOut)
def get_ngo_profile(db: Session = Depends(get_db)):
    return crud.get_ngo_profile(db)


@router.patch("", response_model=schemas.NGOProfileOut)
def update_ngo_profile(payload: schemas.NGOProfileUpdate, db: Session = Depends(get_db)):
    profile = crud.get_ngo_profile(db)
    return crud.update_ngo_profile(db, profile, payload)
