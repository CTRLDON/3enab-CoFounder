"""Shared fixtures: every test gets a fresh SQLite database, decision log and artifact folder."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'mate.db'}")
    monkeypatch.setenv("DECISION_LOG_PATH", str(tmp_path / "decision_log.json"))
    monkeypatch.setenv("ARTIFACTS_DIR", str(tmp_path / "artifacts"))
    monkeypatch.setenv("RESEARCH_ONLINE", "false")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9")  # nothing listens here
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "")  # live ventures must report "not configured", never fake output
    for key in list(os.environ):
        if key.startswith(("STRIPE_", "PAYPAL_")):
            monkeypatch.delenv(key)
    from app.config import get_settings

    get_settings.cache_clear()
    from app.database import configure_engine, init_db

    configure_engine()
    init_db()
    from app.services import gateway_registry
    from app.workflows import phases

    gateway_registry.set_live_gateway(None)
    phases.set_research_service(None)
    yield tmp_path
    get_settings.cache_clear()


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())


def make_founder(client: TestClient, scenario: str = "main", **overrides: Any) -> dict[str, str]:
    from app.demo.scenarios import DEMO_FOUNDERS

    body = {**DEMO_FOUNDERS[scenario], **overrides}
    response = client.post("/api/founders", json=body)
    assert response.status_code == 201, response.text
    return {"X-Founder-Token": response.json()["founder_token"]}


def make_venture(client: TestClient, headers: dict[str, str], mode: str = "demo", scenario: str = "main") -> str:
    response = client.post("/api/ventures", json={"mode": mode, "demo_scenario": scenario}, headers=headers)
    assert response.status_code == 201, response.text
    venture_id = response.json()["id"]
    if mode == "demo":
        assert client.post(f"/api/ventures/{venture_id}/discovery", headers=headers).status_code == 200
    return venture_id


@pytest.fixture
def founder_headers(client: TestClient) -> dict[str, str]:
    return make_founder(client)


def script(client: TestClient, scenario: str = "main") -> dict[str, Any]:
    return client.get("/api/demo/scenarios").json()["scenarios"][scenario]["script"]


def to_workspace(client: TestClient, headers: dict[str, str], scenario: str = "main") -> str:
    """Drive a demo venture from onboarding to an approved plan (main: reject #1, approve #2)."""
    venture_id = make_venture(client, headers, scenario=scenario)
    s = script(client, scenario)
    base = f"/api/ventures/{venture_id}"
    if scenario == "main":
        for line in s["debate"][:3]:
            assert client.post(f"{base}/debate", json={"message": line}, headers=headers).status_code == 200
        first = client.post(f"{base}/proposals", headers=headers).json()["proposal"]
        r = client.post(f"{base}/proposals/{first['id']}/decision", json={"decision": "reject", "reason": s["reject_reason"]}, headers=headers)
        assert r.status_code == 200, r.text
        assert client.post(f"{base}/debate", json={"message": s["debate"][3]}, headers=headers).status_code == 200
    else:
        for line in s["debate"]:
            assert client.post(f"{base}/debate", json={"message": line}, headers=headers).status_code == 200
    proposal = client.post(f"{base}/proposals", headers=headers).json()["proposal"]
    r = client.post(f"{base}/proposals/{proposal['id']}/decision", json={"decision": "approve", "reason": ""}, headers=headers)
    assert r.status_code == 200, r.text
    return venture_id


def ok(response: Any) -> Any:
    assert response.status_code < 300, response.text
    return response.json()
