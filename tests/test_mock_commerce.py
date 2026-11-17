"""Sale to cash is MOCKED end to end: approval-gated, idempotent, refund revokes, reconciles."""

from __future__ import annotations

import re
from pathlib import Path

from conftest import ok, to_workspace

ROOT = Path(__file__).resolve().parents[1]


def _to_launch(client, headers):
    vid = to_workspace(client, headers)
    base = f"/api/ventures/{vid}"
    ok(client.post(f"{base}/phases/1/run", headers=headers)); ok(client.post(f"{base}/phases/1/gate", headers=headers))
    exp = ok(client.post(f"{base}/phases/2/run", headers=headers))["phases"][1]["experiments"][0]
    ok(client.post(f"{base}/experiments/{exp['id']}/results", json={"observed": 6, "source": "mocked"}, headers=headers))
    ok(client.post(f"{base}/phases/2/gate", headers=headers))
    ok(client.post(f"{base}/phases/3/run", headers=headers)); ok(client.post(f"{base}/phases/3/gate", headers=headers))
    ok(client.post(f"{base}/phases/4/run", headers=headers))
    ok(client.post(f"{base}/approvals", json={"subject_type": "commercial_setup", "decision": "approve"}, headers=headers))
    ok(client.post(f"{base}/phases/4/gate", headers=headers))
    ok(client.post(f"{base}/phases/5/run", headers=headers))
    return base


def test_mock_purchase_requires_launch_approval(client, founder_headers):
    base = _to_launch(client, founder_headers)
    r = client.post(f"{base}/mock-commerce/orders", headers=founder_headers)
    assert r.status_code == 403 and r.json()["error"] == "approval_required"


def test_delivery_is_idempotent_and_refund_revokes_access(client, founder_headers):
    base = _to_launch(client, founder_headers)
    ok(client.post(f"{base}/approvals", json={"subject_type": "launch_package", "decision": "approve"}, headers=founder_headers))
    order = ok(client.post(f"{base}/mock-commerce/orders", headers=founder_headers))
    assert order["mocked"] is True and order["label"] == "MOCKED" and order["buyer"].startswith("synthetic-buyer")
    first = ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/deliver", json={"event_id": "evt-a"}, headers=founder_headers))
    again = ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/deliver", json={"event_id": "evt-a"}, headers=founder_headers))
    other = ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/deliver", json={"event_id": "evt-b"}, headers=founder_headers))
    assert again["duplicate_event"] is True and other["duplicate_event"] is True
    assert first["entitlement"]["access_key"] == again["entitlement"]["access_key"] == other["entitlement"]["access_key"]

    refund = ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/refund", json={"event_id": "evt-r"}, headers=founder_headers))
    assert refund["access_revoked"] is True and refund["status"] == "mock_refunded"
    replay = ok(client.post(f"{base}/mock-commerce/orders/{order['id']}/refund", json={"event_id": "evt-r"}, headers=founder_headers))
    assert replay["duplicate_event"] is True

    overview = ok(client.get(f"{base}/mock-commerce", headers=founder_headers))
    recon = overview["reconciliation"]
    assert recon["balanced"] and recon["totals"]["refund"] == -order["amount"]
    assert overview["orders"][0]["entitlement"]["status"] == "revoked"
    # A refunded order cannot be delivered again.
    assert client.post(f"{base}/mock-commerce/orders/{order['id']}/deliver", json={"event_id": "evt-c"}, headers=founder_headers).status_code == 403


def test_no_payment_provider_code_or_endpoints_exist(client):
    source = "\n".join(p.read_text() for p in (ROOT / "backend" / "app").rglob("*.py") if "safety.py" not in p.name)
    assert not re.search(r"import\s+(stripe|paypal|braintree)|api\.stripe\.com|paypal\.com|paymob\.com", source, re.I)
    routes = client.get("/openapi.json").json()["paths"]
    assert not [path for path in routes if re.search(r"payment|checkout|charge|payout", path)]
    requirements = (ROOT / "backend" / "requirements.txt").read_text().lower()
    assert "stripe" not in requirements and "paypal" not in requirements


def test_payment_credentials_in_the_environment_fail_the_launch_gate(client, founder_headers, monkeypatch):
    base = _to_launch(client, founder_headers)
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_placeholder")
    gate = ok(client.post(f"{base}/phases/5/gate", headers=founder_headers))["gate"]
    assert gate["outcome"] == "STOP"
    assert any(c["id"] == "no_payment_credentials" and not c["passed"] for c in gate["checks"])
