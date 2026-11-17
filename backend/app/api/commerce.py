"""MOCKED commerce (purchase, delivery, replay, refund, reconciliation), external-action guard, support."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import orchestrator
from app.errors import Forbidden, InvalidTransition, NotFound
from app.models import MockEventReceipt, MockOrder, SupportTicket
from app.schemas.agent_io import CommercialPack
from app.schemas.api import ExternalActionIn, MockEventIn, SupportTicketIn
from app.services import mock_delivery, mock_payments
from app.services.external_actions import request_external_action
from app.services.mock_reconcile import reconcile
from app.workflows.gates import latest_artifact
from app.workflows.orchestrator import Orchestrator
from app.workflows.phases import triage_ticket

router = APIRouter(prefix="/api/ventures/{venture_id}", tags=["mock-commerce"])
COMMERCE_STATES = {"LAUNCH_SIMULATION", "OPERATING"}


def _require_commerce_state(orch: Orchestrator) -> None:
    if orch.venture.state not in COMMERCE_STATES:
        raise InvalidTransition("MOCKED commerce runs in the Launch phase (or later).")


def _log(orch: Orchestrator, action: str, detail: dict[str, Any], approved: bool = True) -> None:
    orch.audit.record(orch.db, venture_id=orch.venture.id, agent="mock_commerce", action=action, execution_mode="mocked",
                      approved_by="founder" if approved else None, detail=detail)


@router.get("/mock-commerce")
def overview(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    orders = orch.db.scalars(select(MockOrder).where(MockOrder.venture_id == orch.venture.id).order_by(MockOrder.created_at))
    return {"label": "MOCKED", "orders": [mock_payments.order_view(o, mock_delivery.entitlement_for(orch.db, o.id)) for o in orders],
            "reconciliation": reconcile(orch.db, orch.venture.id)}


@router.post("/mock-commerce/orders", status_code=201)
def mock_purchase(orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    _require_commerce_state(orch)
    commercial = latest_artifact(orch.db, orch.venture.id, "commercial_pack")
    if commercial is None:
        raise InvalidTransition("Set pricing in Phase 4 first.")
    pack = CommercialPack.model_validate_json(commercial.content)
    tier = next((t for t in pack.tiers if t.price > 0), pack.tiers[0])
    order = mock_payments.create_mock_order(orch.db, orch.venture, sku=tier.name, amount=tier.price, currency=tier.currency)
    _log(orch, "mock_purchase", {"order_id": order.id, "amount": order.amount, "currency": order.currency})
    orch.db.commit()
    return mock_payments.order_view(order)


@router.post("/mock-commerce/orders/{order_id}/deliver")
def mock_deliver(order_id: str, body: MockEventIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    _require_commerce_state(orch)
    order = mock_payments.get_order(orch.db, orch.venture.id, order_id)
    result, duplicate = mock_delivery.deliver(orch.db, order, event_id=body.event_id)
    _log(orch, "mock_delivery_replayed" if duplicate else "mock_delivery", {"order_id": order.id, "event_id": body.event_id})
    if duplicate:
        count = len(list(orch.db.scalars(select(MockEventReceipt).where(MockEventReceipt.order_id == order.id,
                                                                        MockEventReceipt.kind == "delivery"))))
        entitlement_rows = 1 if mock_delivery.entitlement_for(orch.db, order.id) else 0
        passed = entitlement_rows == 1
        orch.save_artifact(5, "mock_idempotency_check", "MOCKED idempotency check", "json",
                           json.dumps({"order_id": order.id, "event_id": body.event_id, "delivery_events_recorded": count,
                                       "entitlements_for_order": entitlement_rows, "passed": passed}),
                           ["MOCKED"], {"passed": passed, "order_id": order.id})
    orch.db.commit()
    return {**result, "duplicate_event": duplicate}


@router.post("/mock-commerce/orders/{order_id}/refund")
def mock_refund(order_id: str, body: MockEventIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    _require_commerce_state(orch)
    order = mock_payments.get_order(orch.db, orch.venture.id, order_id)
    result, duplicate = mock_payments.refund_mock_order(orch.db, order, event_id=body.event_id)
    _log(orch, "mock_refund_replayed" if duplicate else "mock_refund", {"order_id": order.id, "event_id": body.event_id})
    orch.db.commit()
    return {**result, "duplicate_event": duplicate}


@router.post("/external-actions")
def external_action(body: ExternalActionIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    result = request_external_action(orch.db, orch.venture, kind=body.kind, target=body.target, content=body.content)
    orch.audit.record(orch.db, venture_id=orch.venture.id, agent="external_action_guard", action=f"{body.kind}_not_executed",
                      execution_mode="mocked", approved_by="founder", detail=result)
    orch.db.commit()
    return result


@router.get("/support-tickets")
def tickets(orch: Orchestrator = Depends(orchestrator)) -> list[dict[str, Any]]:
    rows = orch.db.scalars(select(SupportTicket).where(SupportTicket.venture_id == orch.venture.id).order_by(SupportTicket.created_at))
    return [{"id": t.id, "subject": t.subject, "body": t.body, "source": t.source, "category": t.category,
             "draft_reply": t.draft_reply, "status": t.status, "labels": ["MOCKED"] if t.source == "mocked" else []} for t in rows]


@router.post("/support-tickets", status_code=201)
def create_ticket(body: SupportTicketIn, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    if orch.venture.state != "OPERATING":
        raise InvalidTransition("Support runs in Phase 6 (Operate and learn).")
    if body.source == "mocked" and orch.venture.mode != "demo":
        raise Forbidden("MOCKED tickets are only allowed in demo ventures.")
    ticket = SupportTicket(venture_id=orch.venture.id, subject=body.subject, body=body.body, source=body.source)
    orch.db.add(ticket)
    orch.db.flush()
    triage_ticket(orch, ticket)
    orch.db.commit()
    return {"id": ticket.id, "category": ticket.category, "draft_reply": ticket.draft_reply, "status": ticket.status,
            "note": "Draft reply only. Mate does not send messages; copy it and reply yourself after review."}


@router.get("/mock-commerce/orders/{order_id}")
def get_order(order_id: str, orch: Orchestrator = Depends(orchestrator)) -> dict[str, Any]:
    order = orch.db.get(MockOrder, order_id)
    if order is None or order.venture_id != orch.venture.id:
        raise NotFound("Mock order not found.")
    if order.status not in {"mock_paid", "mock_refunded"}:
        raise Forbidden("Unknown order state.")
    return mock_payments.order_view(order, mock_delivery.entitlement_for(orch.db, order.id))
