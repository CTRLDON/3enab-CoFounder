"""The real Ollama HTTP client path: structured output, retries, errors, streaming."""

from __future__ import annotations

import httpx
import pytest
from fake_ollama import FakeOllama, live_gateway

from app.schemas.agent_io import GateCommentary
from app.services.ollama_client import ModelOutputError, ModelRequest, ModelUnavailableError, extract_json_object

REQ = ModelRequest(agent="gatekeeper", task="t", system="sys", messages=[{"role": "user", "content": "hi"}])


def test_structured_output_is_validated_and_tokens_counted():
    fake = FakeOllama([{"commentary": "ok", "suggested_next_steps": ["a"]}])
    result = live_gateway(fake).generate_structured(REQ, GateCommentary)
    assert result.data.commentary == "ok"
    assert result.model == "qwen3.5:9b" and result.execution_mode == "live_ollama"
    assert result.prompt_tokens == 120 and result.completion_tokens == 80
    sent = fake.requests[0]
    assert sent["model"] == "qwen3.5:9b" and sent["stream"] is False
    assert sent["format"]["properties"]["commentary"]  # JSON schema passed as structured-output format
    assert sent["messages"][0] == {"role": "system", "content": "sys"}
    assert sent["think"] is False


def test_malformed_output_is_retried_with_the_validation_error():
    fake = FakeOllama(["not json at all", {"wrong": 1}, {"commentary": "fixed"}])
    result = live_gateway(fake).generate_structured(REQ, GateCommentary)
    assert result.data.commentary == "fixed" and result.attempts == 3
    assert "did not match the required JSON schema" in fake.requests[1]["messages"][-1]["content"]


def test_persistently_malformed_output_raises_instead_of_inventing():
    fake = FakeOllama(["nope", "still nope", "never"])
    with pytest.raises(ModelOutputError):
        live_gateway(fake).generate_structured(REQ, GateCommentary)


def test_missing_model_and_unreachable_server_raise_unavailable():
    fake = FakeOllama([httpx.Response(404, json={"error": "model 'qwen3.5:9b' not found"})])
    with pytest.raises(ModelUnavailableError, match="ollama pull"):
        live_gateway(fake).generate_structured(REQ, GateCommentary)

    def boom(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    from app.config import get_settings
    from app.services.ollama_client import OllamaGateway

    with pytest.raises(ModelUnavailableError, match="not reachable"):
        OllamaGateway(get_settings(), transport=httpx.MockTransport(boom)).generate_structured(REQ, GateCommentary)


def test_timeout_is_reported_as_unavailable():
    def slow(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    from app.config import get_settings
    from app.services.ollama_client import OllamaGateway

    with pytest.raises(ModelUnavailableError, match="did not answer"):
        OllamaGateway(get_settings(), transport=httpx.MockTransport(slow)).generate_structured(REQ, GateCommentary)


def test_models_without_thinking_support_are_retried_without_the_flag():
    fake = FakeOllama([httpx.Response(400, json={"error": "model does not support thinking"}), {"commentary": "ok"}])
    gateway = live_gateway(fake)
    assert gateway.generate_structured(REQ, GateCommentary).data.commentary == "ok"
    assert "think" in fake.requests[0] and "think" not in fake.requests[1]


def test_status_reports_whether_the_model_is_installed():
    assert live_gateway(FakeOllama(models=["qwen3.5:9b"])).status()["model_installed"] is True
    missing = live_gateway(FakeOllama(models=["llama3:8b"])).status()
    assert missing["reachable"] is True and missing["model_installed"] is False and "ollama pull" in missing["detail"]


def test_streaming_yields_chunks():
    lines = b'{"message":{"content":"Hel"},"done":false}\n{"message":{"content":"lo"},"done":true}\n'
    fake = FakeOllama()
    fake.on_chat = lambda body: httpx.Response(200, content=lines)
    assert "".join(live_gateway(fake).stream_text("sys", [{"role": "user", "content": "x"}])) == "Hello"


def test_json_extraction_tolerates_fences_and_thinking():
    assert extract_json_object('<think>hmm</think>```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json_object('Sure! {"a": 2} done') == {"a": 2}
