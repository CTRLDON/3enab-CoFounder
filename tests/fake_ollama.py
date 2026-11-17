"""A scripted stand-in for the Ollama HTTP API, served through httpx.MockTransport.

The real OllamaGateway (HTTP client, retries, schema validation, token accounting) runs unchanged;
only the network is replaced. Values here are test fixtures, not data about anything real.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import httpx


class FakeOllama:
    def __init__(self, replies: list[Any] | None = None, models: list[str] | None = None) -> None:
        self.replies = list(replies or [])
        self.models = models if models is not None else ["qwen3.5:9b"]
        self.requests: list[dict[str, Any]] = []
        self.on_chat: Callable[[dict[str, Any]], httpx.Response] | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": m} for m in self.models]})
        if request.url.path == "/api/chat":
            body = json.loads(request.content)
            self.requests.append(body)
            if self.on_chat:
                return self.on_chat(body)
            if not self.replies:
                return httpx.Response(500, json={"error": "no scripted reply"})
            reply = self.replies.pop(0)
            if isinstance(reply, httpx.Response):
                return reply
            content = reply if isinstance(reply, str) else json.dumps(reply)
            return httpx.Response(200, json={"message": {"role": "assistant", "content": content}, "done": True,
                                             "prompt_eval_count": 120, "eval_count": 80})
        return httpx.Response(404)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)


def live_gateway(fake: FakeOllama):
    from app.config import get_settings
    from app.services.ollama_client import OllamaGateway

    return OllamaGateway(get_settings(), transport=fake.transport())
