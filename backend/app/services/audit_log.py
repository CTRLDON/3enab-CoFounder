"""Audit trail: every agent action and important transition becomes an AuditEvent row and one entry
in decision_log.json with the five keys the hackathon requires (action, sources, model, cost,
approved_by) plus timestamp, agent and, where relevant, the gate outcome and execution mode.

Cost: the Gemini API free tier and local Ollama inference have no per-call fee, so `cost` is 0.0 USD. That figure excludes
electricity and hardware, which are real but not metered per call (see README, "Cost per run").
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import AuditEvent, utcnow

_LOCK = threading.Lock()


def _iso(dt) -> str:  # type: ignore[no-untyped-def]
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def decision_log_entry(event: AuditEvent) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "timestamp": _iso(event.timestamp),
        "agent": event.agent,
        "action": event.action,
        "sources": list(event.sources or []),
        "model": event.model,
        "cost": round(float(event.cost or 0.0), 4),
        "approved_by": event.approved_by,
    }
    if event.outcome:
        entry["outcome"] = event.outcome.lower()
    entry["execution_mode"] = event.execution_mode
    if event.venture_id:
        entry["venture_id"] = event.venture_id
    return entry


class DecisionLogWriter:
    """Appends entries to a JSON array file atomically (write to temp file, then rename)."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"decision log at {self.path} is not valid JSON: {exc}") from exc
        if not isinstance(data, list):
            raise RuntimeError(f"decision log at {self.path} must be a JSON array")
        return data

    def append(self, entry: dict[str, Any]) -> None:
        with _LOCK:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            entries = self.read()
            entries.append(entry)
            fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".decision_log.", suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(entries, handle, indent=2)
                handle.write("\n")
            os.replace(tmp, self.path)


class AuditLogger:
    def __init__(self, log_path: Path | None = None) -> None:
        self.writer = DecisionLogWriter(log_path or get_settings().decision_log_path)

    def record(
        self,
        db: Session,
        *,
        venture_id: str | None,
        agent: str,
        action: str,
        execution_mode: str,
        sources: list[str] | None = None,
        model: str | None = None,
        cost: float = 0.0,
        approved_by: str | None = None,
        outcome: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            venture_id=venture_id,
            timestamp=utcnow(),
            agent=agent,
            action=action,
            sources=[s for s in (sources or []) if s],
            model=model,
            cost=cost,
            approved_by=approved_by,
            outcome=outcome,
            execution_mode=execution_mode,
            detail=detail or {},
        )
        db.add(event)
        db.flush()
        self.writer.append(decision_log_entry(event))
        return event
