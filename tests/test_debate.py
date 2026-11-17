"""Debate behaviour: persistence, live model failures, structured output, proposals."""

from __future__ import annotations

from fake_ollama import FakeOllama, live_gateway

from app.services import gateway_registry
from conftest import make_founder, make_venture, ok, script

INSIGHTS = {"summary": "s", "strengths": [], "limitations": [], "constraints": [], "advantage_areas": [], "open_questions": []}
TURN = {"message": "Who exactly pays for this, and what do they use today?", "stance": "CHALLENGE",
        "key_question": "Who pays?", "assumptions": [{"statement": "People will pay", "classification": "ASSUMPTION", "why_it_matters": "x"}],
        "readiness": {"problem_defined": True}, "recommend_proposal": False}


def test_conversation_history_is_persisted(client, founder_headers):
    vid = make_venture(client, founder_headers)
    line = script(client)["debate"][0]
    ok(client.post(f"/api/ventures/{vid}/debate", json={"message": line}, headers=founder_headers))
    messages = ok(client.get(f"/api/ventures/{vid}/conversation", headers=founder_headers))["messages"]
    assert [m["role"] for m in messages] == ["founder", "agent"]
    assert messages[1]["structured"]["stance"] == "CHALLENGE"
    assert messages[1]["structured"]["readiness_complete"] is False


def test_live_model_failure_is_reported_not_replaced(client, founder_headers):
    vid = make_venture(client, founder_headers, mode="live")  # OLLAMA_BASE_URL points at a closed port
    r = client.post(f"/api/ventures/{vid}/discovery", headers=founder_headers)
    assert r.status_code == 503 and r.json()["error"] == "agent_failure"
    assert r.json()["detail"]["reason"] == "model_unavailable"
    venture = ok(client.get(f"/api/ventures/{vid}", headers=founder_headers))
    assert venture["state"] == "ONBOARDING"  # nothing advanced on a failed call
    audit = ok(client.get(f"/api/ventures/{vid}/audit", headers=founder_headers))
    assert audit["agent_runs"][0]["status"] == "failed"
    assert any(e["action"].endswith(":failed") for e in audit["events"])


def test_live_debate_uses_the_real_gateway_and_validates_output(client, founder_headers):
    fake = FakeOllama([INSIGHTS, "garbage", TURN])
    gateway_registry.set_live_gateway(live_gateway(fake))
    vid = make_venture(client, founder_headers, mode="live")
    ok(client.post(f"/api/ventures/{vid}/discovery", headers=founder_headers))
    reply = ok(client.post(f"/api/ventures/{vid}/debate", json={"message": "I want to build a ChatGPT competitor."}, headers=founder_headers))
    assert reply["reply"]["content"].startswith("Who exactly pays")
    assert "FOUNDER PROFILE" in fake.requests[-1]["messages"][-2]["content"] or "FOUNDER PROFILE" in fake.requests[1]["messages"][-1]["content"]
    runs = ok(client.get(f"/api/ventures/{vid}/audit", headers=founder_headers))["agent_runs"]
    debate_run = [r for r in runs if r["task"] == "debate_turn"][0]
    assert debate_run["attempts"] == 2 and debate_run["model"] == "qwen3.5:9b" and debate_run["prompt_tokens"] == 240


def test_proposal_requires_debate_and_moves_to_awaiting_approval(client, founder_headers):
    vid = make_venture(client, founder_headers)
    assert client.post(f"/api/ventures/{vid}/proposals", headers=founder_headers).status_code == 409
    ok(client.post(f"/api/ventures/{vid}/debate", json={"message": script(client)["debate"][0]}, headers=founder_headers))
    result = ok(client.post(f"/api/ventures/{vid}/proposals", headers=founder_headers))
    assert result["proposal"]["status"] == "awaiting"
    assert result["venture"]["state"] == "AWAITING_FOUNDER_APPROVAL"
    # The founder must decide before the discussion continues.
    assert client.post(f"/api/ventures/{vid}/debate", json={"message": "more"}, headers=founder_headers).status_code == 409


def test_opportunity_scores_are_computed_in_code(client, founder_headers):
    vid = make_venture(client, founder_headers)
    ok(client.post(f"/api/ventures/{vid}/debate", json={"message": script(client)["debate"][0]}, headers=founder_headers))
    result = ok(client.post(f"/api/ventures/{vid}/opportunities", headers=founder_headers))
    indexes = [o["heuristic_index"] for o in result["opportunities"]]
    assert indexes == sorted(indexes, reverse=True) and all(0 <= i <= 100 for i in indexes)
    assert {o["budget_check"] for o in result["opportunities"]} <= {"within_budget", "stretch", "exceeds_budget", "unknown"}
