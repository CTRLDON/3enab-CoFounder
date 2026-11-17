"""Founder approval is enforced in backend code."""

from __future__ import annotations

import pytest

from app.errors import Forbidden
from conftest import make_founder, make_venture, ok, script, to_workspace


def _awaiting(client, headers):
    vid = make_venture(client, headers)
    ok(client.post(f"/api/ventures/{vid}/debate", json={"message": script(client)["debate"][0]}, headers=headers))
    proposal = ok(client.post(f"/api/ventures/{vid}/proposals", headers=headers))["proposal"]
    return vid, proposal


def test_rejected_proposal_creates_no_plan_and_reopens_debate(client, founder_headers):
    vid, proposal = _awaiting(client, founder_headers)
    result = ok(client.post(f"/api/ventures/{vid}/proposals/{proposal['id']}/decision",
                            json={"decision": "reject", "reason": "Too broad"}, headers=founder_headers))
    assert result["venture"]["state"] == "DEBATE" and result["plan"] is None
    assert client.get(f"/api/ventures/{vid}/plan", headers=founder_headers).status_code == 404
    messages = ok(client.get(f"/api/ventures/{vid}/conversation", headers=founder_headers))["messages"]
    assert "Too broad" in messages[-1]["content"] and len(messages) >= 3  # context preserved


def test_approved_proposal_creates_the_workspace(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    venture = ok(client.get(f"/api/ventures/{vid}", headers=founder_headers))
    assert venture["state"] == "WORKSPACE_ACTIVE" and venture["plan_version"] == 1
    plan = ok(client.get(f"/api/ventures/{vid}/plan", headers=founder_headers))
    ids = {n["id"] for n in plan["document"]["nodes"]}
    assert {"venture", "revenue", "costs", "market", "risks", "revenue-stream-1"} <= ids
    actions = [e["action"] for e in ok(client.get(f"/api/ventures/{vid}/audit", headers=founder_headers))["events"]]
    assert "approve:proposal" in actions and "create_plan_v1" in actions


def test_direct_plan_creation_cannot_bypass_approval(client, founder_headers):
    vid, _ = _awaiting(client, founder_headers)
    r = client.post(f"/api/ventures/{vid}/plan", headers=founder_headers)
    assert r.status_code == 403 and r.json()["error"] == "approval_required"


def test_proposal_cannot_be_decided_twice(client, founder_headers):
    vid, proposal = _awaiting(client, founder_headers)
    url = f"/api/ventures/{vid}/proposals/{proposal['id']}/decision"
    ok(client.post(url, json={"decision": "reject"}, headers=founder_headers))
    assert client.post(url, json={"decision": "approve"}, headers=founder_headers).status_code == 409


def test_another_founder_cannot_touch_the_venture(client, founder_headers):
    vid, proposal = _awaiting(client, founder_headers)
    intruder = make_founder(client)
    r = client.post(f"/api/ventures/{vid}/proposals/{proposal['id']}/decision", json={"decision": "approve"}, headers=intruder)
    assert r.status_code == 403
    assert client.post(f"/api/ventures/{vid}/proposals/{proposal['id']}/decision", json={"decision": "approve"}).status_code == 401


def test_agents_cannot_record_approvals(client, founder_headers):
    from app.database import session_factory
    from app.models import Venture
    from app.services.audit_log import AuditLogger
    from app.workflows.approval import record_decision

    vid, proposal = _awaiting(client, founder_headers)
    db = session_factory()()
    venture = db.get(Venture, vid)
    with pytest.raises(Forbidden):
        record_decision(db, venture, subject_type="proposal", subject_id=proposal["id"], decision="approve",
                        actor="skeptical_cofounder", reason="", audit=AuditLogger())
    db.close()


def test_prohibited_category_cannot_be_approved_even_by_the_founder(client, founder_headers):
    from app.database import session_factory
    from app.models import BusinessProposal

    vid, proposal = _awaiting(client, founder_headers)
    db = session_factory()()
    row = db.get(BusinessProposal, proposal["id"])
    row.data = {**row.data, "product_category": "Crypto trading signals app", "one_liner": "Bitcoin investment tips"}
    db.commit()
    db.close()
    r = client.post(f"/api/ventures/{vid}/proposals/{proposal['id']}/decision", json={"decision": "approve"}, headers=founder_headers)
    assert r.status_code == 403 and r.json()["error"] == "policy_violation"
    assert ok(client.get(f"/api/ventures/{vid}", headers=founder_headers))["plan_version"] is None
