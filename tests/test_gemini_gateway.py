"""The real Gemini HTTP client path against a fake Gemini API (httpx.MockTransport). No key or network needed."""

from __future__ import annotations

import json

import httpx
import pytest

from app.config import get_settings
from app.schemas.agent_io import GateCommentary
from app.services.gemini_client import GeminiGateway, to_gemini_contents
from app.services.ollama_client import ModelOutputError, ModelRequest, ModelUnavailableError

REQ = ModelRequest(agent="gatekeeper", task="t", system="sys", messages=[{"role": "user", "content": "hi"}])


def reply(obj, usage=(100, 50)):
    text = obj if isinstance(obj, str) else json.dumps(obj)
    return httpx.Response(200, json={"candidates": [{"content": {"role": "model", "parts": [{"text": text}]}, "finishReason": "STOP"}],
                                     "usageMetadata": {"promptTokenCount": usage[0], "candidatesTokenCount": usage[1]}})


class FakeGemini:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.responses.pop(0)

    def body(self, i):
        return json.loads(self.requests[i].content)


def gateway(fake, key="test-key", **overrides):
    settings = get_settings().model_copy(update={"gemini_api_key": key, **overrides})
    sleeps: list[float] = []
    gw = GeminiGateway(settings, transport=httpx.MockTransport(fake), sleep=sleeps.append)
    gw.sleeps = sleeps  # type: ignore[attr-defined]
    return gw


def test_structured_request_and_validated_result():
    fake = FakeGemini([reply({"commentary": "ok"})])
    result = gateway(fake).generate_structured(REQ, GateCommentary)
    assert result.data.commentary == "ok" and result.execution_mode == "live_gemini" and result.model == "gemini-2.5-flash"
    assert result.prompt_tokens == 100 and result.completion_tokens == 50
    req = fake.requests[0]
    assert req.url.path == "/v1beta/models/gemini-2.5-flash:generateContent"
    assert req.headers["x-goog-api-key"] == "test-key" and "test-key" not in str(req.url)
    body = fake.body(0)
    assert body["systemInstruction"]["parts"][0]["text"] == "sys"
    assert body["generationConfig"]["responseMimeType"] == "application/json"
    assert body["generationConfig"]["responseJsonSchema"]["properties"]["commentary"]
    assert body["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_missing_key_is_reported_without_a_request():
    fake = FakeGemini([])
    with pytest.raises(ModelUnavailableError, match="GEMINI_API_KEY is not set"):
        gateway(fake, key="").generate_structured(REQ, GateCommentary)
    assert not fake.requests


def test_malformed_output_is_retried_then_fails_honestly():
    fake = FakeGemini([reply("not json"), reply({"commentary": "fixed"})])
    result = gateway(fake).generate_structured(REQ, GateCommentary)
    assert result.attempts == 2 and result.data.commentary == "fixed"
    contents = fake.body(1)["contents"]
    assert contents[1]["role"] == "model" and "did not match" in contents[2]["parts"][0]["text"]
    with pytest.raises(ModelOutputError):
        gateway(FakeGemini([reply("x"), reply("y"), reply("z")])).generate_structured(REQ, GateCommentary)


def test_rate_limit_waits_for_the_suggested_delay_then_gives_up():
    limited = httpx.Response(429, json={"error": {"code": 429, "message": "Resource exhausted", "status": "RESOURCE_EXHAUSTED",
                                                  "details": [{"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7s"}]}})
    gw = gateway(FakeGemini([limited, reply({"commentary": "after wait"})]))
    assert gw.generate_structured(REQ, GateCommentary).data.commentary == "after wait"
    assert gw.sleeps == [7.0]
    with pytest.raises(ModelUnavailableError, match="rate limit"):
        gateway(FakeGemini([limited, limited, limited])).generate_structured(REQ, GateCommentary)


def test_schema_rejection_falls_back_to_json_mode_with_schema_in_prompt():
    bad = httpx.Response(400, json={"error": {"code": 400, "message": "Invalid JSON payload: responseJsonSchema unsupported", "status": "INVALID_ARGUMENT"}})
    fake = FakeGemini([bad, bad, reply({"commentary": "ok"})])
    assert gateway(fake).generate_structured(REQ, GateCommentary).data.commentary == "ok"
    second = fake.body(2)
    assert "responseJsonSchema" not in second["generationConfig"]
    assert "JSON schema" in second["systemInstruction"]["parts"][0]["text"]


def test_bad_key_missing_model_and_network_errors():
    bad_key = httpx.Response(400, json={"error": {"code": 400, "message": "API key not valid. Please pass a valid API key.", "status": "INVALID_ARGUMENT"}})
    with pytest.raises(ModelUnavailableError, match="rejected the key"):
        gateway(FakeGemini([bad_key])).generate_structured(REQ, GateCommentary)
    with pytest.raises(ModelUnavailableError, match="not available"):
        gateway(FakeGemini([httpx.Response(404, json={"error": {"message": "models/x is not found"}})])).generate_structured(REQ, GateCommentary)

    def boom(_):
        raise httpx.ConnectError("down")

    with pytest.raises(ModelUnavailableError, match="not reachable"):
        gateway(boom).generate_structured(REQ, GateCommentary)


def test_blocked_answer_counts_as_invalid_output():
    blocked = httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(ModelOutputError):
        gateway(FakeGemini([blocked, blocked, blocked])).generate_structured(REQ, GateCommentary)


def test_status_checks_key_and_model():
    assert gateway(FakeGemini([]), key="").status()["detail"].startswith("GEMINI_API_KEY is not set")
    assert gateway(FakeGemini([httpx.Response(200, json={"name": "models/gemini-2.5-flash"})])).status()["model_installed"] is True
    assert "rejected the key" in gateway(FakeGemini([httpx.Response(403, json={})])).status()["detail"]


def test_contents_alternate_and_start_with_user():
    contents = to_gemini_contents([{"role": "assistant", "content": "a"}, {"role": "user", "content": "b"}, {"role": "user", "content": "c"}])
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[2]["parts"][0]["text"] == "b\n\nc"


def test_live_venture_runs_through_gemini(client, founder_headers):
    from app.services import gateway_registry
    from conftest import make_venture, ok

    insights = {"summary": "s", "strengths": [], "limitations": [], "constraints": [], "advantage_areas": [], "open_questions": []}
    fake = FakeGemini([reply(insights)])
    gateway_registry.set_live_gateway(gateway(fake))
    vid = make_venture(client, founder_headers, mode="live")
    ok(client.post(f"/api/ventures/{vid}/discovery", headers=founder_headers))
    runs = ok(client.get(f"/api/ventures/{vid}/audit", headers=founder_headers))["agent_runs"]
    assert runs[0]["model"] == "gemini-2.5-flash" and runs[0]["execution_mode"] == "live_gemini"
    assert "FOUNDER PROFILE" in fake.body(0)["contents"][-1]["parts"][0]["text"]


def test_system_status_never_exposes_the_key(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "super-secret-value")
    get_settings.cache_clear()
    from app.services import gateway_registry

    gateway_registry.set_live_gateway(None)
    body = client.get("/api/system/status?check_model=false").text
    assert "super-secret-value" not in body and '"provider":"gemini"' in body


def test_generic_invalid_argument_tries_simpler_requests_before_failing():
    invalid = httpx.Response(400, json={"error": {"code": 400, "message": "Request contains an invalid argument.", "status": "INVALID_ARGUMENT"}})
    # thinking dropped -> still 400; schema dropped (thinking restored) -> works
    fake = FakeGemini([invalid, invalid, reply({"commentary": "ok"})])
    gw = gateway(fake)
    assert gw.generate_structured(REQ, GateCommentary).data.commentary == "ok"
    first, second, third = (fake.body(i)["generationConfig"] for i in range(3))
    assert "thinkingConfig" in first and "responseJsonSchema" in first
    assert "thinkingConfig" not in second and "responseJsonSchema" in second
    assert "thinkingConfig" in third and "responseJsonSchema" not in third
    # The working shape is remembered for the next call.
    fake.responses.append(reply({"commentary": "again"}))
    gw.generate_structured(REQ, GateCommentary)
    assert "responseJsonSchema" not in fake.body(3)["generationConfig"]


def test_invalid_argument_on_every_shape_reports_googles_message():
    invalid = httpx.Response(400, json={"error": {"code": 400, "message": "Request contains an invalid argument.", "status": "INVALID_ARGUMENT"}})
    fake = FakeGemini([invalid] * 4)
    with pytest.raises(ModelUnavailableError, match="invalid argument"):
        gateway(fake).generate_structured(REQ, GateCommentary)
    assert len(fake.requests) == 4
