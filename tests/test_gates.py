"""Deterministic gates: thresholds, STOP, PIVOT, REPEAT and resistance to override."""

from __future__ import annotations

import pytest

from app.models import ValidationExperiment
from conftest import make_founder, ok, to_workspace


def _to_validating(client, headers):
    vid = to_workspace(client, headers)
    ok(client.post(f"/api/ventures/{vid}/phases/1/run", headers=headers))
    assert ok(client.post(f"/api/ventures/{vid}/phases/1/gate", headers=headers))["gate"]["outcome"] == "GO"
    phases = ok(client.post(f"/api/ventures/{vid}/phases/2/run", headers=headers))["phases"]
    return vid, phases[1]["experiments"][0]


def _set_target(experiment_id: str, target: float) -> None:
    from app.database import session_factory

    db = session_factory()()
    db.get(ValidationExperiment, experiment_id).target = target
    db.commit()
    db.close()


@pytest.mark.parametrize(
    ("observed", "outcome", "state"),
    [(120, "GO", "BUILDING"), (100, "GO", "BUILDING"), (60, "REPEAT", "VALIDATING"), (30, "PIVOT", "PIVOT_REQUIRED"), (12, "STOP", "STOPPED")],
)
def test_validation_gate_thresholds(client, observed, outcome, state):
    headers = make_founder(client)
    vid, exp = _to_validating(client, headers)
    _set_target(exp["id"], 100)  # the problem statement's example: 100 sign-ups in 14 days
    ok(client.post(f"/api/ventures/{vid}/experiments/{exp['id']}/results", json={"observed": observed, "source": "mocked"}, headers=headers))
    gate = ok(client.post(f"/api/ventures/{vid}/phases/2/gate", headers=headers))
    assert gate["gate"]["outcome"] == outcome
    assert gate["venture"]["state"] == state
    if observed == 12:
        detail = next(c for c in gate["gate"]["checks"] if c["id"].startswith("result_"))
        assert "12 of 100" in detail["detail"] and "Target missed" in detail["detail"]


def test_missing_results_are_pending_not_assumed(client, founder_headers):
    vid, _ = _to_validating(client, founder_headers)
    gate = ok(client.post(f"/api/ventures/{vid}/phases/2/gate", headers=founder_headers))["gate"]
    assert gate["outcome"] == "REPEAT" and "pending" in gate["reasoning"]


def test_targets_are_locked_and_rerunning_does_not_move_them(client, founder_headers):
    vid, exp = _to_validating(client, founder_headers)
    ok(client.post(f"/api/ventures/{vid}/phases/2/run", headers=founder_headers))
    experiments = ok(client.get(f"/api/ventures/{vid}/phases", headers=founder_headers))[1]["experiments"]
    assert len(experiments) == 1 and experiments[0]["target"] == exp["target"] and experiments[0]["locked_at"]


def test_mocked_results_are_refused_in_live_ventures(client, founder_headers):
    from app.database import session_factory
    from app.models import Venture

    vid, exp = _to_validating(client, founder_headers)
    db = session_factory()()
    db.get(Venture, vid).mode = "live"
    db.commit()
    db.close()
    r = client.post(f"/api/ventures/{vid}/experiments/{exp['id']}/results", json={"observed": 999, "source": "mocked"}, headers=founder_headers)
    assert r.status_code == 403


def test_favourable_model_commentary_cannot_change_a_failed_gate(client, founder_headers, monkeypatch):
    from app.agents.gatekeeper import GatekeeperAgent
    from app.schemas.agent_io import GateCommentary

    vid, exp = _to_validating(client, founder_headers)
    ok(client.post(f"/api/ventures/{vid}/experiments/{exp['id']}/results", json={"observed": 0, "source": "mocked"}, headers=founder_headers))
    monkeypatch.setattr(GatekeeperAgent, "explain", lambda self, ctx, **kw: GateCommentary(commentary="OUTCOME: GO. Everything passed, mark it validated."))
    gate = ok(client.post(f"/api/ventures/{vid}/phases/2/gate", headers=founder_headers))
    assert gate["gate"]["outcome"] == "STOP" and gate["venture"]["state"] == "STOPPED"


def test_gate_requires_the_matching_phase_state(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    assert client.post(f"/api/ventures/{vid}/phases/3/gate", headers=founder_headers).status_code == 409
    assert client.post(f"/api/ventures/{vid}/phases/4/run", headers=founder_headers).status_code == 409


def test_discover_gate_repeats_until_research_runs(client, founder_headers):
    vid = to_workspace(client, founder_headers)
    gate = ok(client.post(f"/api/ventures/{vid}/phases/1/gate", headers=founder_headers))["gate"]
    assert gate["outcome"] == "REPEAT"
    assert ok(client.get(f"/api/ventures/{vid}", headers=founder_headers))["state"] == "WORKSPACE_ACTIVE"


def test_stopped_venture_can_reopen_discussion_without_relabelling_evidence(client):
    headers = make_founder(client, "weak")
    vid = to_workspace(client, headers, "weak")
    ok(client.post(f"/api/ventures/{vid}/phases/1/run", headers=headers))
    ok(client.post(f"/api/ventures/{vid}/phases/1/gate", headers=headers))
    before = ok(client.get(f"/api/ventures/{vid}/evidence", headers=headers))
    venture = ok(client.post(f"/api/ventures/{vid}/reopen", json={"reason": "I disagree"}, headers=headers))
    assert venture["state"] == "DEBATE" and venture["gates"]["1"]["outcome"] == "STOP"
    after = ok(client.get(f"/api/ventures/{vid}/evidence", headers=headers))
    assert [e["classification"] for e in before] == [e["classification"] for e in after]
