from __future__ import annotations

from conftest import ok


def test_valid_profile_is_persisted(client):
    body = {"display_name": "Sara", "profile": {"resources": {"budget_amount": 500, "budget_currency": "usd", "weekly_hours": 10},
                                                 "preferences": {"starting_idea": "A tool for choirs", "target_country": "Kenya"}}}
    created = ok(client.post("/api/founders", json=body))
    headers = {"X-Founder-Token": created["founder_token"]}
    me = ok(client.get("/api/founders/me", headers=headers))
    assert me["display_name"] == "Sara"
    assert me["profile"]["resources"]["budget_currency"] == "USD"
    assert me["profile"]["preferences"]["target_country"] == "Kenya"


def test_missing_optional_fields_get_defaults(client):
    created = ok(client.post("/api/founders", json={"display_name": "Lee"}))
    assert created["profile"]["resources"]["budget_amount"] is None
    assert created["profile"]["preferences"]["has_idea"] is True


def test_invalid_input_is_rejected_with_field_messages(client):
    r = client.post("/api/founders", json={"display_name": "  ", "profile": {"resources": {"budget_currency": "EUROS", "weekly_hours": 400}}})
    assert r.status_code == 422
    fields = {p["field"] for p in r.json()["detail"]}
    assert "display_name" in fields
    assert any(f.endswith("budget_currency") for f in fields)
    assert any(f.endswith("weekly_hours") for f in fields)


def test_profile_update_increments_revision(client):
    created = ok(client.post("/api/founders", json={"display_name": "Ana"}))
    headers = {"X-Founder-Token": created["founder_token"]}
    profile = created["profile"]
    profile["background"]["skills"] = ["Design"]
    updated = ok(client.put("/api/founders/me/profile", json=profile, headers=headers))
    assert updated["profile_revision"] == 2 and updated["profile"]["background"]["skills"] == ["Design"]


def test_requests_without_or_with_wrong_token_are_refused(client):
    assert client.get("/api/founders/me").status_code == 401
    assert client.get("/api/founders/me", headers={"X-Founder-Token": "nope"}).status_code == 401
