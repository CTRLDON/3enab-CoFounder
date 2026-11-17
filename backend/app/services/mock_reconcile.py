"""MOCKED reconciliation: matches mock orders, charges, synthetic fees, refunds, payouts and access."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MockLedgerEntry, MockOrder
from app.services.mock_delivery import entitlement_for


def reconcile(db: Session, venture_id: str) -> dict[str, Any]:
    orders = list(db.scalars(select(MockOrder).where(MockOrder.venture_id == venture_id).order_by(MockOrder.created_at)))
    ledger = list(db.scalars(select(MockLedgerEntry).where(MockLedgerEntry.venture_id == venture_id)))
    by_order: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for entry in ledger:
        by_order[entry.order_id][entry.kind] += entry.amount

    rows, mismatches = [], []
    totals: dict[str, float] = defaultdict(float)
    for order in orders:
        sums = by_order[order.id]
        entitlement = entitlement_for(db, order.id)
        expected_access = "active" if order.status == "mock_paid" else "revoked"
        access = entitlement.status if entitlement else "none"
        if order.status == "mock_paid" and entitlement is None:
            mismatches.append(f"{order.id}: paid but not delivered")
        elif order.status == "mock_refunded" and entitlement is None:
            pass  # refunded before delivery: nothing to revoke
        elif access != expected_access:
            mismatches.append(f"{order.id}: access is {access}, expected {expected_access}")
        if abs(sums["charge"] - order.amount) > 0.005:
            mismatches.append(f"{order.id}: charge {sums['charge']} does not match order amount {order.amount}")
        if order.status == "mock_refunded" and abs(sums["refund"] + order.amount) > 0.005:
            mismatches.append(f"{order.id}: refund missing or wrong")
        net = round(sums["charge"] + sums["fee"] + sums["refund"], 2)
        for kind in ("charge", "fee", "refund"):
            totals[kind] += sums[kind]
        totals["payout"] += net
        rows.append(
            {
                "order_id": order.id,
                "buyer": order.buyer_label,
                "status": order.status,
                "charge": round(sums["charge"], 2),
                "fee": round(sums["fee"], 2),
                "refund": round(sums["refund"], 2),
                "mock_payout": net,
                "access": access,
                "currency": order.currency,
            }
        )
    return {
        "label": "MOCKED",
        "mocked": True,
        "note": "Synthetic records only. No payment provider, no money, no payouts exist.",
        "orders": rows,
        "totals": {k: round(v, 2) for k, v in totals.items()},
        "mismatches": mismatches,
        "balanced": not mismatches,
    }
