"""AI-negotiated node edits: explicit approval, versioning, optimistic concurrency."""

from __future__ import annotations

from conftest import ok, script, to_workspace


def _negotiate(client, headers, vid):
    s = script(client)
    session = ok(client.post(f"/api/ventures/{vid}/negotiations", json={"node_id": "revenue", "message": s["negotiation"][0]}, headers=headers))
    assert session["status"] == "open"
    assert session["messages"][-1]["structured"]["position"] == "DISAGREE"
    session = ok(client.post(f"/api/ventures/{vid}/negotiations/{session['id']}/messages", json={"message": s["negotiation"][1]}, headers=headers))
    assert session["status"] == "proposed"
    return session


def test_approved_revision_creates_a_new_version(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    session = _negotiate(client, founder_headers, vid)
    # Nothing changed yet: the AI cannot apply its own proposal.
    assert ok(client.get(f"/api/ventures/{vid}/plan", headers=founder_headers))["current_version"] == 1
    result = ok(client.post(f"/api/ventures/{vid}/negotiations/{session['id']}/decision",
                            json={"decision": "approve", "expected_version": 1}, headers=founder_headers))
    assert result["plan"]["current_version"] == 2
    node = next(n for n in result["plan"]["document"]["nodes"] if n["id"] == "revenue-stream-1")
    assert node["title"] == "Per-term subscription per centre"
    detail = ok(client.get(f"/api/ventures/{vid}/plan/nodes/revenue", headers=founder_headers))
    assert detail["history"][0]["to_version"] == 2 and detail["history"][0]["approved_by"] == "founder"
    v1 = ok(client.get(f"/api/ventures/{vid}/plan?version=1", headers=founder_headers))
    assert next(n for n in v1["document"]["nodes"] if n["id"] == "revenue-stream-1")["title"].startswith("Monthly")


def test_rejected_revision_leaves_the_plan_unchanged(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    session = _negotiate(client, founder_headers, vid)
    result = ok(client.post(f"/api/ventures/{vid}/negotiations/{session['id']}/decision",
                            json={"decision": "reject", "expected_version": 1}, headers=founder_headers))
    assert result["plan"]["current_version"] == 1 and result["negotiation"]["status"] == "rejected"


def test_stale_version_is_refused(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    first = _negotiate(client, founder_headers, vid)
    second = _negotiate(client, founder_headers, vid)
    ok(client.post(f"/api/ventures/{vid}/negotiations/{first['id']}/decision", json={"decision": "approve", "expected_version": 1}, headers=founder_headers))
    r = client.post(f"/api/ventures/{vid}/negotiations/{second['id']}/decision", json={"decision": "approve", "expected_version": 1}, headers=founder_headers)
    assert r.status_code == 409 and r.json()["error"] == "version_conflict"
    assert ok(client.get(f"/api/ventures/{vid}/plan", headers=founder_headers))["current_version"] == 2


def test_invalid_ai_changes_are_rejected_by_the_validator():
    from app.schemas.agent_io import NodeFieldChange
    from app.services.plan_versioning import validate_changes

    doc = {"nodes": [{"id": "revenue"}]}
    problems = validate_changes(doc, [
        NodeFieldChange(node_id="ghost", field="summary", value="x"),
        NodeFieldChange(node_id="revenue", field="risks", value="not a list"),
        NodeFieldChange(node_id="revenue", field="economic_class", value="profit-machine"),
    ])
    assert len(problems) == 3


def test_unknown_node_cannot_be_negotiated(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    r = client.post(f"/api/ventures/{vid}/negotiations", json={"node_id": "nope", "message": "change"}, headers=founder_headers)
    assert r.status_code == 404
