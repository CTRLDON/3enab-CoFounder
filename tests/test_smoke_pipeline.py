"""Smoke test: the whole six-phase pipeline runs through real orchestration, gates and approvals."""

from __future__ import annotations

import json

from conftest import make_founder, ok, script, to_workspace

REQUIRED_KEYS = {"timestamp", "agent", "action", "sources", "model", "cost", "approved_by"}


def test_main_scenario_runs_all_six_phases(client, isolated_env):
    headers = make_founder(client)
    vid = to_workspace(client, headers)
    base = f"/api/ventures/{vid}"
    s = script(client)

    ok(client.post(f"{base}/phases/1/run", headers=headers))
    assert ok(client.post(f"{base}/phases/1/gate", headers=headers))["gate"]["outcome"] == "GO"

    phases = ok(client.post(f"{base}/phases/2/run", headers=headers))["phases"]
    experiment = phases[1]["experiments"][0]
    ok(client.post(f"{base}/experiments/{experiment['id']}/results", json={"observed": 6, "source": "mocked"}, headers=headers))
    assert ok(client.post(f"{base}/phases/2/gate", headers=headers))["gate"]["outcome"] == "GO"

    build = ok(client.post(f"{base}/phases/3/run", headers=headers))["result"]
    assert build["tests_failed"] == 0 and build["tests_passed"] > 5
    assert ok(client.post(f"{base}/phases/3/gate", headers=headers))["gate"]["outcome"] == "GO"

    ok(client.post(f"{base}/phases/4/run", headers=headers))
    assert ok(client.post(f"{base}/phases/4/gate", headers=headers))["gate"]["outcome"] == "REPEAT"  # waits for the founder
    ok(client.post(f"{base}/approvals", json={"subject_type": "commercial_setup", "decision": "approve"}, headers=headers))
    assert ok(client.post(f"{base}/phases/4/gate", headers=headers))["gate"]["outcome"] == "GO"

    ok(client.post(f"{base}/phases/5/run", headers=headers))
    ok(client.post(f"{base}/approvals", json={"subject_type": "launch_package", "decision": "approve"}, headers=headers))
    order = ok(client.post(f"{base}/mock-commerce/orders", headers=headers))
    ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/deliver", json={"event_id": "evt-1"}, headers=headers))
    ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/deliver", json={"event_id": "evt-1"}, headers=headers))
    second = ok(client.post(f"{base}/mock-commerce/orders", headers=headers))
    ok(client.post(f"{base}/mock-commerce/orders/{second['id']}/deliver", json={"event_id": "evt-2"}, headers=headers))
    ok(client.post(f"{base}/mock-commerce/orders/{second['id']}/refund", json={"event_id": "evt-3"}, headers=headers))
    assert ok(client.post(f"{base}/phases/5/gate", headers=headers))["gate"]["outcome"] == "GO"

    ok(client.post(f"{base}/phases/6/run", headers=headers))
    ok(client.post(f"{base}/support-tickets", json={**s["support_ticket"], "source": "mocked"}, headers=headers))
    gate6 = ok(client.post(f"{base}/phases/6/gate", headers=headers))["gate"]
    assert gate6["outcome"] == "GO" and gate6["evidence_basis"] == "mocked"
    assert ok(client.get(base, headers=headers))["state"] == "OPERATING"

    log = json.loads((isolated_env / "decision_log.json").read_text())
    assert len(log) > 40
    assert all(REQUIRED_KEYS <= entry.keys() for entry in log)
    assert all(isinstance(e["sources"], list) and isinstance(e["cost"], (int, float)) for e in log)
    assert {e["outcome"] for e in log if "outcome" in e} >= {"go", "repeat"}


def test_weak_idea_is_stopped_by_the_discover_gate(client):
    headers = make_founder(client, "weak")
    vid = to_workspace(client, headers, "weak")
    base = f"/api/ventures/{vid}"
    ok(client.post(f"{base}/phases/1/run", headers=headers))
    gate = ok(client.post(f"{base}/phases/1/gate", headers=headers))
    assert gate["gate"]["outcome"] == "STOP"
    assert gate["venture"]["state"] == "STOPPED"
    failed = {c["id"] for c in gate["gate"]["checks"] if not c["passed"]}
    assert {"capital_vs_budget", "founder_fit", "recommendation"} <= failed
    # A stopped venture cannot run the next phase.
    assert client.post(f"{base}/phases/2/run", headers=headers).status_code == 409
