"""Shared API dependencies: database session, founder authentication, venture ownership."""

from __future__ import annotations

import hashlib
import secrets
from collections.abc import Iterator

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Forbidden, NotFound, Unauthorized
from app.models import Founder, Venture
from app.services.audit_log import AuditLogger
from app.workflows.orchestrator import Orchestrator


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def db_session() -> Iterator[Session]:
    yield from get_db()


def current_founder(
    x_founder_token: str | None = Header(default=None), db: Session = Depends(db_session)
) -> Founder:
    if not x_founder_token:
        raise Unauthorized("Missing X-Founder-Token header.")
    founder = db.scalars(select(Founder).where(Founder.token_hash == hash_token(x_founder_token))).first()
    if founder is None:
        raise Unauthorized("Unknown founder token.")
    return founder


def owned_venture(venture_id: str, founder: Founder = Depends(current_founder), db: Session = Depends(db_session)) -> Venture:
    venture = db.get(Venture, venture_id)
    if venture is None:
        raise NotFound("Venture not found.")
    if venture.founder_id != founder.id:
        raise Forbidden("This venture belongs to another founder.")
    return venture


def orchestrator(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> Orchestrator:
    return Orchestrator(db, venture, AuditLogger())
