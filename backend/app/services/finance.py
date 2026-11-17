"""Deterministic break-even scenarios from the Commercial agent's assumptions.

Inputs are ASSUMPTIONS; outputs are PROJECTIONS. Nothing here is a forecast or a promise.
"""

from __future__ import annotations

import math
from typing import Any

from app.schemas.agent_io import CommercialPack, PriceTier

PERIOD_MONTHS = {"monthly": 1, "quarterly": 3, "per_term_4_months": 4, "yearly": 12}
SCENARIO_CUSTOMERS = [5, 10, 20, 40]


def monthly_price(tier: PriceTier) -> float | None:
    if tier.period == "one_time":
        return None
    return tier.price / PERIOD_MONTHS[tier.period]


def break_even(pack: CommercialPack) -> dict[str, Any]:
    paid = [t for t in pack.tiers if t.price > 0]
    if not paid:
        return {"viable": False, "reason": "No paid tier is defined.", "classification": "PROJECTION"}
    tier = paid[0]
    mismatched = sorted({c.currency for c in pack.cost_assumptions if c.currency != tier.currency})
    if mismatched:
        return {
            "viable": False,
            "reason": f"Costs use {', '.join(mismatched)} but the price uses {tier.currency}; convert them before relying on break-even.",
            "classification": "PROJECTION",
        }

    fixed_monthly = sum(c.amount for c in pack.cost_assumptions if c.kind == "fixed_monthly")
    one_time = sum(c.amount for c in pack.cost_assumptions if c.kind == "one_time")
    variable = sum(c.amount for c in pack.cost_assumptions if c.kind == "variable_per_sale")

    recurring = monthly_price(tier)
    if recurring is None:  # one-time purchase: each sale contributes once
        contribution = tier.price - variable
        unit = "sales per month"
    else:
        contribution = recurring - variable / PERIOD_MONTHS[tier.period]
        unit = "paying customers"
    if contribution <= 0:
        return {
            "viable": False,
            "reason": f"Each {unit[:-1] if unit.endswith('s') else unit} loses money: price does not cover variable cost.",
            "tier": tier.name,
            "contribution_per_unit_monthly": round(contribution, 2),
            "classification": "PROJECTION",
        }

    needed = math.ceil(fixed_monthly / contribution) if fixed_monthly > 0 else 0
    scenarios = []
    for customers in SCENARIO_CUSTOMERS:
        net = customers * contribution - fixed_monthly
        payback = math.ceil(one_time / net) if net > 0 and one_time > 0 else (0 if net > 0 else None)
        scenarios.append(
            {
                "customers": customers,
                "monthly_revenue": round(customers * (recurring if recurring is not None else tier.price), 2),
                "monthly_net": round(net, 2),
                "months_to_recover_one_time_costs": payback,
            }
        )
    return {
        "viable": True,
        "tier": tier.name,
        "currency": tier.currency,
        "price": tier.price,
        "period": tier.period,
        "monthly_equivalent_price": round(recurring if recurring is not None else tier.price, 2),
        "fixed_monthly_costs": round(fixed_monthly, 2),
        "one_time_costs": round(one_time, 2),
        "variable_cost_per_sale": round(variable, 2),
        "contribution_per_unit_monthly": round(contribution, 2),
        "break_even_units": needed,
        "break_even_unit_label": unit,
        "scenarios": scenarios,
        "classification": "PROJECTION",
        "note": "Projection computed from ASSUMPTION inputs. Not a forecast and not a promise of income.",
    }
