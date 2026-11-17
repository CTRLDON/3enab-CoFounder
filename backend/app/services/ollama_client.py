"""Model gateway: the only code that talks to a language model.

`OllamaGateway` calls a local Ollama server over HTTP (never exposed to the browser) and asks for
JSON that matches a Pydantic schema. Output is validated, malformed output is retried with the
validation error as feedback, and failures are raised — never replaced with invented content.

`GeminiGateway` (gemini_client.py) and `ScriptedDemoGateway` (app/demo/scripted_gateway.py) implement the same interface for the
clearly-labelled offline demo mode.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings

T = TypeVar("T", bound=BaseModel)

LIVE_MODE = "live_ollama"
SCRIPTED_MODE = "scripted_demo"


class ModelUnavailableError(RuntimeError):
    """Ollama is unreachable, the model is not pulled, or the call timed out."""


class ModelOutputError(RuntimeError):
    """The model answered, but not with valid JSON for the schema after all retries."""


@dataclass
class ModelResult(Generic[T]):
    data: T
    model: str | None
    execution_mode: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    attempts: int = 1
    duration_ms: int = 0


@dataclass
class ModelRequest:
    agent: str
    task: str
    system: str
    messages: list[dict[str, str]]
    script_turn: int = 0
    scenario: str | None = None


class ModelGateway(Protocol):
    execution_mode: str

    def generate_structured(self, request: ModelRequest, schema: type[T]) -> ModelResult[T]: ...


_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL)


def extract_json_object(text: str) -> Any:
    """Parse a JSON object from model text, tolerating code fences and stray thinking blocks."""
    cleaned = _THINK_BLOCK.sub("", text).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.DOTALL).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


class OllamaGateway:
    execution_mode = LIVE_MODE

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.ollama_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.ollama_timeout_seconds, connect=5.0),
            transport=transport,
        )
        self._think_supported: bool = True

    # --- discovery --------------------------------------------------------------------------

    def list_models(self) -> list[str]:
        try:
            response = self._client.get("/api/tags", timeout=5.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama is not reachable at {self.settings.ollama_base_url}: {exc}") from exc
        return [entry.get("name", "") for entry in response.json().get("models", [])]

    def status(self) -> dict[str, Any]:
        model = self.settings.ollama_model
        try:
            installed = self.list_models()
        except ModelUnavailableError as exc:
            return {"provider": "ollama", "reachable": False, "model": model, "model_installed": False, "installed": [], "detail": str(exc)}
        normalized = {name if ":" in name else f"{name}:latest" for name in installed}
        wanted = model if ":" in model else f"{model}:latest"
        return {
            "provider": "ollama",
            "reachable": True,
            "model": model,
            "model_installed": wanted in normalized,
            "installed": sorted(installed),
            "detail": None if wanted in normalized else f"Model '{model}' is not pulled yet. Run: ollama pull {model}",
        }

    # --- generation -------------------------------------------------------------------------

    def _payload(self, messages: list[dict[str, str]], schema: dict[str, Any] | None, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "stream": stream,
            "options": {"temperature": self.settings.ollama_temperature},
        }
        if schema is not None:
            payload["format"] = schema
        if self._think_supported:
            payload["think"] = self.settings.ollama_think
        return payload

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._client.post("/api/chat", json=payload)
        except httpx.TimeoutException as exc:
            raise ModelUnavailableError(
                f"Ollama did not answer within {self.settings.ollama_timeout_seconds:.0f}s."
            ) from exc
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama is not reachable at {self.settings.ollama_base_url}: {exc}") from exc

        if response.status_code >= 400:
            body = response.text[:500]
            if "think" in body.lower() and "think" in payload:
                # Model does not support the thinking switch: retry once without it.
                self._think_supported = False
                payload = {k: v for k, v in payload.items() if k != "think"}
                return self._post_chat(payload)
            if response.status_code == 404 or "not found" in body.lower():
                raise ModelUnavailableError(
                    f"Model '{self.settings.ollama_model}' is not available in Ollama. "
                    f"Run: ollama pull {self.settings.ollama_model}"
                )
            raise ModelUnavailableError(f"Ollama returned HTTP {response.status_code}: {body}")
        return response.json()

    def generate_structured(self, request: ModelRequest, schema: type[T]) -> ModelResult[T]:
        json_schema = schema.model_json_schema()
        conversation: list[dict[str, str]] = [{"role": "system", "content": request.system}, *request.messages]
        prompt_tokens = completion_tokens = 0
        started = time.perf_counter()
        last_error = "no attempt made"
        attempts = 0

        for attempt in range(1, self.settings.ollama_max_retries + 2):
            attempts = attempt
            data = self._post_chat(self._payload(conversation, json_schema, stream=False))
            prompt_tokens += int(data.get("prompt_eval_count") or 0)
            completion_tokens += int(data.get("eval_count") or 0)
            content = (data.get("message") or {}).get("content", "")
            try:
                parsed = schema.model_validate(extract_json_object(content))
                return ModelResult(
                    data=parsed,
                    model=self.settings.ollama_model,
                    execution_mode=LIVE_MODE,
                    prompt_tokens=prompt_tokens or None,
                    completion_tokens=completion_tokens or None,
                    attempts=attempts,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)[:800]
                conversation = [
                    *conversation,
                    {"role": "assistant", "content": content[:4000]},
                    {
                        "role": "user",
                        "content": (
                            "Your previous reply did not match the required JSON schema. "
                            f"Validation error: {last_error}\nReply again with only one valid JSON object."
                        ),
                    },
                ]
        raise ModelOutputError(
            f"{request.agent}/{request.task}: model output invalid after {attempts} attempts ({last_error})"
        )

    def stream_text(self, system: str, messages: list[dict[str, str]]) -> Iterator[str]:
        """Stream free text token by token (used for long-form drafts; structured calls are not streamed)."""
        payload = self._payload([{"role": "system", "content": system}, *messages], None, stream=True)
        try:
            with self._client.stream("POST", "/api/chat", json=payload) as response:
                if response.status_code >= 400:
                    raise ModelUnavailableError(f"Ollama returned HTTP {response.status_code}")
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    piece = (chunk.get("message") or {}).get("content", "")
                    if piece:
                        yield piece
                    if chunk.get("done"):
                        break
        except httpx.HTTPError as exc:
            raise ModelUnavailableError(f"Ollama stream failed: {exc}") from exc
