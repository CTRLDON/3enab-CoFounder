"""MOCKED checkout and refunds.

There is no payment provider, no sandbox, no card data and no money anywhere in this module.
A "mock order" is an internal synthetic record created only after the founder approved the
launch package; every response carries mocked=True and the label MOCKED.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import Forbidden, NotFound
from app.models import MockEventReceipt, MockLedgerEntry, MockOrder, Venture
from app.services import mock_delivery
from app.workflows.approval import require_approval

MOCK_LABEL = "MOCKED"
SYNTHETIC_FEE_RATE = 0.03  # ASSUMPTION used only to exercise fee reconciliation; not a real provider's fee


def order_view(order: MockOrder, entitlement: Any = None) -> dict[str, Any]:
    return {
        "id": order.id,
        "label": MOCK_LABEL,
        "mocked": True,
        "buyer": order.buyer_label,
        "sku": order.product_sku,
        "amount": order.amount,
        "currency": order.currency,
        "status": order.status,
        "entitlement": mock_delivery.entitlement_view(entitlement) if entitlement else None,
    }


def create_mock_order(db: Session, venture: Venture, *, sku: str, amount: float, currency: str) -> MockOrder:
    approval = require_approval(db, venture.id, "launch_package")
    if amount < 0:
        raise Forbidden("Amount cannot be negative.")
    count = db.scalar(select(func.count()).select_from(MockOrder).where(MockOrder.venture_id == venture.id)) or 0
    order = MockOrder(
        venture_id=venture.id,
        buyer_label=f"synthetic-buyer-{count + 1}",
        product_sku=sku,
        amount=round(amount, 2),
        currency=currency,
        status="mock_paid",
        approval_id=approval.id,
    )
    db.add(order)
    db.flush()
    fee = round(amount * SYNTHETIC_FEE_RATE, 2)
    db.add_all(
        [
            MockLedgerEntry(venture_id=venture.id, order_id=order.id, kind="charge", amount=order.amount, currency=currency),
            MockLedgerEntry(venture_id=venture.id, order_id=order.id, kind="fee", amount=-fee, currency=currency),
        ]
    )
    db.flush()
    return order


def get_order(db: Session, venture_id: str, order_id: str) -> MockOrder:
    order = db.get(MockOrder, order_id)
    if order is None or order.venture_id != venture_id:
        raise NotFound("Mock order not found.")
    return order


def refund_mock_order(db: Session, order: MockOrder, *, event_id: str) -> tuple[dict[str, Any], bool]:
    """Idempotent: replaying the same refund event returns the first result unchanged."""
    receipt = db.get(MockEventReceipt, event_id)
    if receipt is not None:
        if receipt.order_id != order.id or receipt.kind != "refund":
            raise Forbidden("This event id was already used for a different mock event.")
        return receipt.result, True
    if order.status == "mock_refunded":
        result = {"order_id": order.id, "status": order.status, "label": MOCK_LABEL, "note": "Already refunded."}
    else:
        order.status = "mock_refunded"
        db.add(MockLedgerEntry(venture_id=order.venture_id, order_id=order.id, kind="refund", amount=-order.amount, currency=order.currency))
        revoked = mock_delivery.revoke(db, order)
        result = {
            "order_id": order.id,
            "status": order.status,
            "label": MOCK_LABEL,
            "access_revoked": revoked,
            "note": "MOCKED refund recorded. No money moved; access was revoked.",
        }
    db.add(MockEventReceipt(event_id=event_id, order_id=order.id, kind="refund", result=result))
    db.flush()
    return result, False
