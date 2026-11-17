"""Generated artifacts: list, read, sandboxed previews and MVP export."""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import db_session, owned_venture
from app.api.views import artifact_summary
from app.errors import Forbidden, NotFound
from app.models import GeneratedArtifact, Venture

router = APIRouter(prefix="/api/ventures/{venture_id}/artifacts", tags=["artifacts"])

# Generated HTML is shown only inside a sandboxed iframe: no same-origin access, no network.
PREVIEW_CSP = "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; img-src data:; form-action 'none'; base-uri 'none'"


def _artifact(db: Session, venture: Venture, artifact_id: str) -> GeneratedArtifact:
    artifact = db.get(GeneratedArtifact, artifact_id)
    if artifact is None or artifact.venture_id != venture.id:
        raise NotFound("Artifact not found.")
    return artifact


@router.get("")
def list_artifacts(venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> list[dict[str, Any]]:
    rows = db.scalars(select(GeneratedArtifact).where(GeneratedArtifact.venture_id == venture.id).order_by(GeneratedArtifact.created_at))
    return [artifact_summary(a) for a in rows]


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> dict[str, Any]:
    a = _artifact(db, venture, artifact_id)
    content: Any = a.content
    if a.content_type == "bundle":
        content = json.loads(a.content)
    return {**artifact_summary(a), "content": content, "meta": a.meta}


@router.get("/{artifact_id}/preview", response_class=HTMLResponse)
def preview(artifact_id: str, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> HTMLResponse:
    a = _artifact(db, venture, artifact_id)
    if a.content_type != "html":
        raise Forbidden("Only HTML artifacts have a preview.")
    return HTMLResponse(a.content, headers={"Content-Security-Policy": PREVIEW_CSP, "X-Content-Type-Options": "nosniff"})


@router.get("/{artifact_id}/export")
def export_bundle(artifact_id: str, venture: Venture = Depends(owned_venture), db: Session = Depends(db_session)) -> Response:
    a = _artifact(db, venture, artifact_id)
    if a.content_type != "bundle":
        raise Forbidden("Only MVP bundles can be exported as a zip.")
    files: dict[str, str] = json.loads(a.content)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(f"mvp/{name}", content)
    return Response(buffer.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="mvp-{a.id}.zip"'})
