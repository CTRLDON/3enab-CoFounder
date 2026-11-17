from __future__ import annotations

import pytest

from app.errors import InvalidTransition
from app.workflows.state_machine import ALLOWED_TRANSITIONS, VentureState, current_phase


def test_every_state_has_transition_rules():
    assert set(ALLOWED_TRANSITIONS) == set(VentureState)


def test_plan_cannot_be_reached_without_the_approval_state():
    for state, targets in ALLOWED_TRANSITIONS.items():
        if VentureState.PLAN_APPROVED in targets:
            assert state == VentureState.AWAITING_FOUNDER_APPROVAL


def test_invalid_transition_raises(client, founder_headers):
    from app.database import session_factory
    from app.models import Venture
    from app.services.audit_log import AuditLogger
    from app.workflows.state_machine import transition
    from conftest import make_venture

    vid = make_venture(client, founder_headers)
    db = session_factory()()
    venture = db.get(Venture, vid)
    with pytest.raises(InvalidTransition):
        transition(db, venture, VentureState.OPERATING, actor="founder", reason="skip", audit=AuditLogger(), execution_mode="test")
    db.close()


def test_current_phase_mapping():
    assert current_phase("DEBATE") == 1 and current_phase("BUILDING") == 3 and current_phase("STOPPED") is None
