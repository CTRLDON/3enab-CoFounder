"""Markdown/HTML renderers for artifacts. Every market claim is shown with its evidence class."""

from __future__ import annotations

import html
from typing import Any

from app.agents.opportunity_evaluation import CRITERIA_LABELS, CRITERIA_WEIGHTS


def _money(m: dict[str, Any] | None) -> str:
    if not m or m.get("amount") is None:
        return f"UNKNOWN ({(m or {}).get('classification', 'UNKNOWN')})"
    return f"{m['amount']:,.0f} {m['currency']} {m.get('period', '')} — {m.get('classification', 'ASSUMPTION')}".strip()


def bullet(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) or "- (none)"


def proposal_md(p: dict[str, Any], number: int, status: str) -> str:
    expenses = "\n".join(f"| {e['item']} | {_money(e['estimate'])} | {e['estimate'].get('basis', '')} |" for e in p["main_expenses"])
    alts = "\n".join(f"- **{c['name']}** — {c['note']} *(named in debate; existence checked in Phase 1 research)*" for c in p["competitive_alternatives"])
    exp = p["first_experiment"]
    return f"""# Business proposal #{number}: {p['business_name']}

Status: **{status}** · Mate's recommendation: **{p['recommendation'].replace('_', ' ')}**

> {p['one_liner']}

## Problem
{p['problem']}

## Target customer
{p['target_customer']}

## Proposed solution
{p['solution']}

## Founder–idea fit (heuristic {p['founder_fit_score']}/5)
{p['founder_fit']}

## Unique value proposition
{p['value_proposition']}

## Business model and revenue streams
{p['business_model']}

{bullet(p['revenue_streams'])}

## Main expenses (all ASSUMPTION unless marked)
| Item | Estimate | Basis |
|---|---|---|
{expenses}

Estimated start-up capital: {_money(p['estimated_startup_capital'])}. {p['estimated_startup_capital'].get('basis', '')}

## Competitive alternatives
{alts or '- None named.'}

## Major risks
{bullet(p['major_risks'])}

## Missing evidence
{bullet(p['missing_evidence'])}

## First validation experiment
**{exp['name']}** — {exp['method']}
Target: **{exp['target']:g} {exp['metric']} within {exp['window_days']} days** (declared before any results). {exp.get('threshold_rationale', '')}

## Reasons for
{bullet(p['reasons_for'])}

## Reasons against
{bullet(p['reasons_against'])}

## Recommended next action
{p['recommended_next_action']}
"""


def comparison_md(scored: list[dict[str, Any]], summary: str) -> str:
    header = "| Criterion (weight) | " + " | ".join(o["title"] for o in scored) + " |"
    sep = "|---|" + "---|" * len(scored)
    rows = []
    for key, label in CRITERIA_LABELS.items():
        cells = []
        for o in scored:
            score = next((s for s in o["scores"] if s["criterion"] == key), None)
            cells.append(f"{score['score']}/5 — {score['rationale']} ({score['evidence']})" if score else "—")
        rows.append(f"| {label} (×{CRITERIA_WEIGHTS[key]:g}) | " + " | ".join(cells) + " |")
    totals = "| **Heuristic index (0–100)** | " + " | ".join(f"**{o['heuristic_index']}**" for o in scored) + " |"
    budget = "| Budget check | " + " | ".join(o["budget_check"].replace("_", " ") for o in scored) + " |"
    return f"""# Opportunity comparison

{summary}

The index is a weighted average of 1–5 scores (5 = most favourable for this founder), rescaled to 0–100.
It is a heuristic for comparing options — **not** a probability of success. Scores are ASSUMPTIONS unless marked otherwise.

{header}
{sep}
{chr(10).join(rows)}
{totals}
{budget}
"""


def evidence_register_md(records: list[Any], notes: list[str], suggested: list[tuple[str, str]]) -> str:
    rows = []
    for r in records:
        source = f"[{r.source_title or r.source_url}]({r.source_url})" if r.source_url else "—"
        retrieved = r.retrieved_at.strftime("%Y-%m-%d") if r.retrieved_at else "—"
        rows.append(
            f"| {r.claim.replace('|', '/')} | **{r.classification}** | {source} | {retrieved} | {r.confidence} | "
            f"{r.limitations.replace('|', '/')} | {r.node_id or '—'} |"
        )
    sugg = "\n".join(f"- [{name}]({url}) — suggested for manual review (not retrieved)" for name, url in suggested)
    note_text = "\n".join(f"> {n}" for n in notes)
    return f"""# Evidence register

{note_text}

| Claim | Class | Source | Retrieved | Confidence | Limitations | Plan node |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## Suggested sources for this market
{sugg}

Classes: VERIFIED = supported by a retrieved, identifiable source · ESTIMATE = sourced third-party estimate ·
ASSUMPTION = unverified · PROJECTION = modelled scenario · MOCKED = demo data · UNKNOWN = cannot be established yet.
"""


def interview_md(plan: dict[str, Any]) -> str:
    return f"""# Customer interview plan (Mom Test)

**Who:** {plan['target_profile']}

**How to recruit**
{bullet(plan['recruiting_channels'])}

**Questions** (about past behaviour, not opinions of the idea)
{chr(10).join(f'{i}. {q}' for i, q in enumerate(plan['questions'], 1))}

**Avoid**
{bullet(plan['avoid'])}

These are questions for real interviews. Mate never generates interview answers; only transcripts from real
conversations count as evidence.
"""


def lean_canvas_md(c: dict[str, Any], risky: list[dict[str, Any]]) -> str:
    risks = "\n".join(f"| {r['statement']} | {r['risk']} | {r.get('node_id') or '—'} | {r['how_to_test']} |" for r in risky)
    return f"""# Lean Canvas (all entries are ASSUMPTIONS until tested)

| Problem | Solution | Unique value proposition | Unfair advantage | Customer segments |
|---|---|---|---|---|
| {'<br>'.join(c['problem'])} | {'<br>'.join(c['solution'])} | {c['unique_value_proposition']} | {c['unfair_advantage']} | {'<br>'.join(c['customer_segments'])} |

| Key metrics | Channels | Cost structure | Revenue streams |
|---|---|---|---|
| {'<br>'.join(c['key_metrics'])} | {'<br>'.join(c['channels'])} | {'<br>'.join(c['cost_structure'])} | {'<br>'.join(c['revenue_streams'])} |

## Riskiest assumptions
| Assumption | Risk | Plan node | How to test |
|---|---|---|---|
{risks}
"""


PAGE_STYLE = """body{margin:0;font:16px/1.55 system-ui,-apple-system,'Segoe UI',sans-serif;color:#1f2a2a;background:#f7f8f6}
.banner{background:#7a2e1f;color:#fff;padding:10px 16px;font-size:14px}
main{max-width:720px;margin:0 auto;padding:48px 24px}h1{font-size:34px;line-height:1.15;margin:0 0 12px}
.sub{font-size:18px;color:#4d5a59;margin:0 0 28px}ul{padding-left:20px}li{margin:6px 0}
form{margin-top:28px;display:grid;gap:10px;max-width:420px}input{font:inherit;padding:10px;border:1px solid #8c9896;border-radius:6px}
button{font:inherit;padding:10px 14px;border-radius:6px;border:0;background:#2f6f68;color:#fff}button[disabled]{opacity:.6}
.price{font-size:22px;font-weight:600;margin:20px 0 4px}.muted{color:#5b6766;font-size:14px}"""


def landing_page_html(copy: dict[str, Any]) -> str:
    e = html.escape
    benefits = "".join(f"<li>{e(b)}</li>" for b in copy["benefits"])
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(copy['headline'])}</title><style>{PAGE_STYLE}</style></head><body>
<div class="banner">DRAFT landing page — not published. The form below is disabled. Showing this page does not prove demand; only recorded sign-ups count.</div>
<main><h1>{e(copy['headline'])}</h1><p class="sub">{e(copy['subheadline'])}</p><ul>{benefits}</ul>
<form onsubmit="return false"><label>{e(copy['waitlist_question'])}<br><input disabled placeholder="Preview only"></label>
<input disabled type="email" placeholder="Email (preview only)"><button disabled>{e(copy['call_to_action'])}</button></form></main></body></html>"""


def store_page_html(pack: dict[str, Any], price_line: str) -> str:
    e = html.escape
    bullets = "".join(f"<li>{e(b)}</li>" for b in pack["feature_bullets"])
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(pack['store_headline'])}</title><style>{PAGE_STYLE}</style></head><body>
<div class="banner">MOCKED store page — draft, not published. Checkout is MOCKED: no payment is taken and no card details are collected.</div>
<main><h1>{e(pack['store_headline'])}</h1><p class="sub">{e(pack['product_description'])}</p><ul>{bullets}</ul>
<p class="price">{e(price_line)}</p><p class="muted">Prices are proposals under test. Draft policies require legal review.</p>
<button disabled>Buy (MOCKED — use the Launch phase controls in Mate)</button></main></body></html>"""


def gate_md(phase: int, phase_name: str, outcome: str, reasoning: str, basis: str, checks: list[dict[str, Any]],
            commentary: str | None, venture_mode: str) -> str:
    rows = "\n".join(
        f"| {'PASS' if c['passed'] else 'FAIL'} | {c['label']} | {c['severity']} | {c['detail'].replace('|', '/')} |" for c in checks
    )
    mode_note = "Scripted demo run (MOCKED agent responses; deterministic gate code is real)." if venture_mode == "demo" else "Live run with the configured model."
    return f"""# Phase {phase} gate — {phase_name}

**Outcome: {outcome}** (decided by deterministic rules in `backend/app/workflows/gates.py`)

{reasoning}

Evidence basis: `{basis}` · {mode_note}

| Result | Check | Severity | Detail |
|---|---|---|---|
{rows}

## Gatekeeper commentary (explains; cannot change the outcome)
{commentary or 'Unavailable.'}
"""
