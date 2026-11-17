"""Founder onboarding and profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import current_founder, db_session, hash_token, new_token
from app.models import Founder, FounderProfile, utcnow
from app.schemas.founder import FounderCreate, FounderCreated, FounderOut, FounderProfileData

router = APIRouter(prefix="/api/founders", tags=["founders"])


def _out(founder: Founder) -> dict:
    return {"id": founder.id, "display_name": founder.display_name,
            "profile": FounderProfileData.model_validate(founder.profile.data), "profile_revision": founder.profile.revision}


@router.post("", response_model=FounderCreated, status_code=201)
def create_founder(body: FounderCreate, db: Session = Depends(db_session)) -> dict:
    token = new_token()
    founder = Founder(display_name=body.display_name, token_hash=hash_token(token))
    db.add(founder)
    db.flush()
    db.add(FounderProfile(founder_id=founder.id, data=body.profile.model_dump(mode="json")))
    db.commit()
    db.refresh(founder)
    return {**_out(founder), "founder_token": token}


@router.get("/me", response_model=FounderOut)
def me(founder: Founder = Depends(current_founder)) -> dict:
    return _out(founder)


@router.put("/me/profile", response_model=FounderOut)
def update_profile(body: FounderProfileData, founder: Founder = Depends(current_founder), db: Session = Depends(db_session)) -> dict:
    founder.profile.data = body.model_dump(mode="json")
    founder.profile.revision += 1
    founder.profile.updated_at = utcnow()
    db.commit()
    return _out(founder)
