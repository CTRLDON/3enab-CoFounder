"""MOCKED delivery: a paid mock order triggers an access entitlement; a refund revokes it.

Idempotency is enforced twice: by an event receipt table (the same event id never runs twice) and
by a unique constraint on entitlements per order (a second event cannot create a second grant).
"""

from __future__ import annotations

import secrets
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import Forbidden
from app.models import MockEntitlement, MockEventReceipt, MockOrder, utcnow


def entitlement_view(entitlement: MockEntitlement) -> dict[str, Any]:
    return {
        "id": entitlement.id,
        "label": "MOCKED",
        "access_key": entitlement.access_key,
        "status": entitlement.status,
        "revoked_at": entitlement.revoked_at.isoformat() if entitlement.revoked_at else None,
    }


def entitlement_for(db: Session, order_id: str) -> MockEntitlement | None:
    return db.scalars(select(MockEntitlement).where(MockEntitlement.order_id == order_id)).first()


def deliver(db: Session, order: MockOrder, *, event_id: str) -> tuple[dict[str, Any], bool]:
    """Grant access for a mock-paid order. Returns (result, duplicate)."""
    receipt = db.get(MockEventReceipt, event_id)
    if receipt is not None:
        if receipt.order_id != order.id or receipt.kind != "delivery":
            raise Forbidden("This event id was already used for a different mock event.")
        return receipt.result, True
    if order.status != "mock_paid":
        raise Forbidden("Only a mock-paid order can be delivered.")
    existing = entitlement_for(db, order.id)
    duplicate = existing is not None
    entitlement = existing or MockEntitlement(order_id=order.id, access_key=f"MOCKED-{secrets.token_hex(4)}", status="active")
    if not duplicate:
        db.add(entitlement)
        db.flush()
    result = {"order_id": order.id, "entitlement": entitlement_view(entitlement), "label": "MOCKED", "duplicate_event": duplicate}
    db.add(MockEventReceipt(event_id=event_id, order_id=order.id, kind="delivery", result=result))
    db.flush()
    return result, duplicate


def revoke(db: Session, order: MockOrder) -> bool:
    entitlement = entitlement_for(db, order.id)
    if entitlement is None or entitlement.status == "revoked":
        return False
    entitlement.status = "revoked"
    entitlement.revoked_at = utcnow()
    db.flush()
    return True
