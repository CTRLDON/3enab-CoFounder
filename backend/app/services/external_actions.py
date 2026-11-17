"""Guard for anything that would leave the system: publishing, sending, spending, signing.

Two independent locks:
  1. A matching founder approval must exist (enforced here, in code).
  2. No external connector exists in this build, so even an approved action is not executed;
     the response says so and is labelled MOCKED.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.errors import Forbidden, PolicyViolation
from app.models import Venture
from app.services.safety import screen_generated_text
from app.workflows.approval import require_approval

EXTERNAL_KINDS = {"publish", "send", "spend", "sign"}


def action_subject(kind: str, target: str) -> str:
    return f"{kind}:{target.strip().lower()[:80]}"


def request_external_action(db: Session, venture: Venture, *, kind: str, target: str, content: str) -> dict[str, Any]:
    if kind not in EXTERNAL_KINDS:
        raise Forbidden(f"Unknown external action '{kind}'.")
    report = screen_generated_text(content)
    if report.blocked:
        raise PolicyViolation("The content breaks Mate's rules: " + "; ".join(f.message for f in report.findings))
    subject = action_subject(kind, target)
    require_approval(db, venture.id, "external_action", subject)
    executed = False
    if get_settings().external_actions_enabled:  # pragma: no cover — always False in this build
        executed = False
    return {
        "executed": executed,
        "status": "MOCKED_NOT_EXECUTED",
        "label": "MOCKED",
        "subject": subject,
        "reason": "Approved, but external connectors are disabled in this build. Nothing was published, sent or spent.",
    }
