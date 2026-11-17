"""Gemini API gateway (Google AI Studio free tier).

Same contract as OllamaGateway: send the agent's prompt and a Pydantic JSON schema, get validated data back,
retry malformed output with the validation error, and raise ModelUnavailableError / ModelOutputError instead of
ever inventing a result. The API key is read from GEMINI_API_KEY, sent only in the x-goog-api-key header, and never
logged or returned by the API.

Free-tier specifics handled here:
  * HTTP 429 (rate limit): wait for the server's suggested retry delay (capped) and retry a few times.
  * Structured output: `responseJsonSchema` is requested; if the model rejects the schema, the gateway falls back to
    JSON mode with the schema written into the system instruction. Output is validated in code either way.
  * Thinking: disabled by default (thinkingBudget 0) to save time and quota; dropped if the model rejects it.
"""

from __future__ import annotations

import json
import re
import time
from collections.abc import Callable
from typing import Any

import httpx
from pydantic import ValidationError

from app.config import Settings
from app.services.ollama_client import ModelOutputError, ModelRequest, ModelResult, ModelUnavailableError, T, extract_json_object

GEMINI_MODE = "live_gemini"
KEY_HELP = "Create a free key at https://aistudio.google.com/apikey and set GEMINI_API_KEY in .env."


def _retry_delay_seconds(body: dict[str, Any]) -> float | None:
    for detail in (body.get("error") or {}).get("details") or []:
        delay = detail.get("retryDelay")
        if isinstance(delay, str) and (m := re.fullmatch(r"(\d+(?:\.\d+)?)s", delay)):
            return float(m.group(1))
    return None


def to_gemini_contents(messages: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Map chat messages to Gemini contents: assistant -> model, merge same-role runs, start with a user turn."""
    contents: list[dict[str, Any]] = []
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"][0]["text"] += "\n\n" + message["content"]
        else:
            contents.append({"role": role, "parts": [{"text": message["content"]}]})
    if contents and contents[0]["role"] == "model":
        contents.insert(0, {"role": "user", "parts": [{"text": "(Earlier conversation omitted.)"}]})
    return contents


class GeminiGateway:
    execution_mode = GEMINI_MODE

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.settings = settings
        self._client = httpx.Client(
            base_url=settings.gemini_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.gemini_timeout_seconds, connect=10.0),
            transport=transport,
        )
        self._sleep = sleep
        # Optional request settings; switched off automatically if the model rejects them.
        self._json_schema_supported = True
        self._thinking_supported = settings.gemini_thinking_budget >= 0

    @property
    def model(self) -> str:
        return self.settings.gemini_model.removeprefix("models/")

    def _headers(self) -> dict[str, str]:
        key = self.settings.gemini_api_key.strip()
        if not key:
            raise ModelUnavailableError(f"GEMINI_API_KEY is not set. {KEY_HELP}")
        return {"x-goog-api-key": key, "Content-Type": "application/json"}

    # --- status ---------------------------------------------------------------------------

    def status(self) -> dict[str, Any]:
        base = {"provider": "gemini", "model": self.model, "installed": []}
        if not self.settings.gemini_api_key.strip():
            return {**base, "reachable": False, "model_installed": False, "detail": f"GEMINI_API_KEY is not set. {KEY_HELP}"}
        try:
            response = self._client.get(f"/v1beta/models/{self.model}", headers=self._headers(), timeout=10.0)
        except httpx.HTTPError as exc:
            return {**base, "reachable": False, "model_installed": False, "detail": f"Gemini API not reachable: {type(exc).__name__}"}
        if response.status_code == 200:
            return {**base, "reachable": True, "model_installed": True, "detail": None}
        if response.status_code == 404:
            return {**base, "reachable": True, "model_installed": False,
                    "detail": f"Model '{self.model}' is not available to this key. Run scripts/connect-gemini.sh to pick one that is."}
        if response.status_code in (400, 401, 403):
            return {**base, "reachable": True, "model_installed": False, "detail": f"The Gemini API rejected the key. {KEY_HELP}"}
        return {**base, "reachable": True, "model_installed": False, "detail": f"Gemini API returned HTTP {response.status_code}."}

    # --- generation -------------------------------------------------------------------------

    def _payload(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        config: dict[str, Any] = {"temperature": self.settings.ollama_temperature, "responseMimeType": "application/json"}
        instruction = system
        if self._json_schema_supported:
            config["responseJsonSchema"] = schema
        else:
            instruction += "\n\nReply with one JSON object that matches this JSON schema:\n" + json.dumps(schema)
        if self._thinking_supported:
            config["thinkingConfig"] = {"thinkingBudget": self.settings.gemini_thinking_budget}
        return {
            "systemInstruction": {"parts": [{"text": instruction}]},
            "contents": to_gemini_contents(messages),
            "generationConfig": config,
        }

    def _fallback_after_400(self, tried: set[tuple[bool, bool]]) -> bool:
        """After a 400 'invalid argument', switch to the next request shape that has not been tried.

        Models differ in which optional settings they accept (structured-output schema, thinking budget) and
        often answer with a generic "Request contains an invalid argument". Shapes are tried in this order:
        drop thinking; drop the schema (schema goes into the prompt instead); drop both. Validation of the
        output happens in code either way, so no shape weakens the checks.
        """
        thinking_allowed = self.settings.gemini_thinking_budget >= 0
        for js, th in ((self._json_schema_supported, False), (False, thinking_allowed), (False, False)):
            if (js, th) not in tried:
                self._json_schema_supported, self._thinking_supported = js, th
                return True
        return False

    def _generate(self, system: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        rate_retries = self.settings.gemini_rate_limit_retries
        tried: set[tuple[bool, bool]] = set()
        while True:
            tried.add((self._json_schema_supported, self._thinking_supported))
            try:
                response = self._client.post(
                    f"/v1beta/models/{self.model}:generateContent",
                    headers=self._headers(),
                    json=self._payload(system, messages, schema),
                )
            except httpx.TimeoutException as exc:
                raise ModelUnavailableError(f"Gemini did not answer within {self.settings.gemini_timeout_seconds:.0f}s.") from exc
            except httpx.HTTPError as exc:
                raise ModelUnavailableError(f"Gemini API not reachable: {type(exc).__name__}") from exc

            if response.status_code < 400:
                return response.json()
            try:
                body = response.json()
            except ValueError:
                body = {}
            message = str((body.get("error") or {}).get("message") or response.text)[:400]
            lowered = message.lower()

            if response.status_code == 429:
                delay = _retry_delay_seconds(body) or 10.0
                if rate_retries > 0 and delay <= self.settings.gemini_max_rate_limit_wait_seconds:
                    rate_retries -= 1
                    self._sleep(delay)
                    continue
                raise ModelUnavailableError(
                    "Gemini free-tier rate limit or daily quota reached. Wait a minute and try again, "
                    "or choose a model with more free quota (scripts/connect-gemini.sh)."
                )
            if response.status_code in (401, 403) or "api key" in lowered:
                raise ModelUnavailableError(f"The Gemini API rejected the key. {KEY_HELP}")
            if response.status_code == 400 and self._fallback_after_400(tried):
                continue
            if response.status_code == 404:
                raise ModelUnavailableError(f"Gemini model '{self.model}' is not available to this key. "
                                            "Run scripts/connect-gemini.sh to list and pick a model that is.")
            raise ModelUnavailableError(f"Gemini API returned HTTP {response.status_code}: {message}")

    @staticmethod
    def _text(data: dict[str, Any]) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates returned")
            return f"[no answer: {reason}]"
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    def generate_structured(self, request: ModelRequest, schema: type[T]) -> ModelResult[T]:
        json_schema = schema.model_json_schema()
        messages = list(request.messages)
        prompt_tokens = completion_tokens = 0
        started = time.perf_counter()
        last_error = "no attempt made"
        attempts = 0
        for attempt in range(1, self.settings.gemini_max_retries + 2):
            attempts = attempt
            data = self._generate(request.system, messages, json_schema)
            usage = data.get("usageMetadata") or {}
            prompt_tokens += int(usage.get("promptTokenCount") or 0)
            completion_tokens += int(usage.get("candidatesTokenCount") or 0) + int(usage.get("thoughtsTokenCount") or 0)
            content = self._text(data)
            try:
                parsed = schema.model_validate(extract_json_object(content))
                return ModelResult(
                    data=parsed, model=self.model, execution_mode=GEMINI_MODE,
                    prompt_tokens=prompt_tokens or None, completion_tokens=completion_tokens or None,
                    attempts=attempts, duration_ms=int((time.perf_counter() - started) * 1000),
                )
            except (json.JSONDecodeError, ValidationError, ValueError) as exc:
                last_error = str(exc)[:800]
                messages = [
                    *messages,
                    {"role": "assistant", "content": content[:4000] or "(empty reply)"},
                    {"role": "user", "content": "Your previous reply did not match the required JSON schema. "
                                                f"Validation error: {last_error}\nReply again with only one valid JSON object."},
                ]
        raise ModelOutputError(f"{request.agent}/{request.task}: model output invalid after {attempts} attempts ({last_error})")
